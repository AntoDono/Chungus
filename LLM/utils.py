from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count
from .models import APIKey, Model, LLMRequest
from typing import Optional, Dict, List, Union, Any, Literal

ThinkValue = Union[bool, str]
ThinkingLevel = Literal['low', 'medium', 'high', 'max']

THINKING_LEVELS = frozenset({'low', 'medium', 'high', 'max'})
THINKING_DISABLE = frozenset({'false', 'disabled', 'none', 'off', 'nothink'})
THINKING_ENABLE = frozenset({'true', 'enabled', 'on'})
THINKING_DEFAULT = frozenset({'default', 'auto', ''})
import threading
import os
import io
import json
import base64 as _base64
import urllib.request as _urllib_request

from vllm import LLM, SamplingParams
import ollama

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def normalize_thinking_input(value: Any) -> Optional[str]:
    """
    Normalize API thinking/reasoning input to a canonical string, or None for default.
    Accepts bool, str, or None. Raises ValueError for invalid values.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if not isinstance(value, str):
        raise ValueError(f'thinking must be a boolean or string, got {type(value).__name__}')

    normalized = value.strip().lower()
    if normalized in THINKING_DEFAULT:
        return None
    if normalized in THINKING_LEVELS:
        return normalized
    if normalized in THINKING_DISABLE:
        return 'false'
    if normalized in THINKING_ENABLE:
        return 'true'
    raise ValueError(
        f"Invalid thinking value '{value}'. "
        "Use 'default', 'low', 'medium', 'high', 'max', true/false, or enabled/disabled."
    )


def resolve_think_value(
    request_thinking: Any,
    model_thinking_mode: str,
) -> Optional[ThinkValue]:
    """
    Resolve the value to pass to Ollama's think parameter.
    None means omit think (model/provider default).
    """
    if request_thinking is not None:
        normalized = normalize_thinking_input(request_thinking)
        if normalized is None:
            return None
        if normalized == 'true':
            return True
        if normalized == 'false':
            return False
        return normalized

    mode = (model_thinking_mode or 'default').strip().lower()
    if mode in THINKING_DEFAULT:
        return None
    if mode == 'enabled':
        return True
    if mode == 'disabled':
        return False
    if mode in THINKING_LEVELS:
        return mode
    return None


def think_value_for_storage(think_value: Optional[ThinkValue]) -> Optional[str]:
    """Serialize resolved think value for LLMRequest storage."""
    if think_value is None:
        return None
    if isinstance(think_value, bool):
        return 'true' if think_value else 'false'
    return think_value


def apply_think_to_chat_kwargs(chat_kwargs: dict, think_value: Optional[ThinkValue]) -> None:
    """Add Ollama think parameter when a non-default value is resolved."""
    if think_value is not None:
        chat_kwargs['think'] = think_value


def extract_ollama_message_parts(message: Any) -> tuple[str, str]:
    """Return (content, thinking) from an Ollama message object or dict."""
    if message is None:
        return "", ""
    if hasattr(message, 'content'):
        content = message.content or ""
        thinking = getattr(message, 'thinking', None) or ""
    elif isinstance(message, dict):
        content = message.get("content", "") or ""
        thinking = message.get("thinking", "") or ""
    else:
        content, thinking = "", ""
    return content, thinking


class ModelTypeMismatchError(Exception):
    def __init__(self, model_name: str, expected: str, actual: str):
        self.model_name = model_name
        self.expected = expected
        self.actual = actual
        super().__init__(
            f'Model "{model_name}" is not a {expected} model (got {actual})'
        )


class NoActiveModelError(Exception):
    def __init__(self, model_type: str, requested_name: Optional[str] = None):
        self.model_type = model_type
        self.requested_name = requested_name
        if requested_name:
            message = (
                f'No active {model_type} model available '
                f'(requested "{requested_name}" is missing or inactive)'
            )
        else:
            message = f'No active {model_type} model available'
        super().__init__(message)


def resolve_requested_model(
    requested_name: Optional[str],
    model_type: str,
) -> tuple[Model, Optional[str]]:
    """
    Resolve a requested model name to an active Model.
    Falls back to the default active model, then the first active model by name.
    Returns (model, requested_name) when routing away from the requested model.
    """
    routed_from: Optional[str] = None

    if requested_name:
        try:
            model = Model.objects.get(name=requested_name)
            if model.is_active:
                if model.model_type != model_type:
                    raise ModelTypeMismatchError(requested_name, model_type, model.model_type)
                return model, None
            routed_from = requested_name
        except Model.DoesNotExist:
            routed_from = requested_name

    active_models = Model.objects.filter(is_active=True, model_type=model_type)
    fallback = active_models.filter(is_default=True).first()
    if fallback is None:
        fallback = active_models.order_by('name').first()
    if fallback is None:
        raise NoActiveModelError(model_type, routed_from)

    return fallback, routed_from


# Global engine cache - one engine per model
_vllm_engines: Dict[str, Any] = {}
_vllm_embedding_engines: Dict[str, Any] = {}
_engines_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Image helpers (OpenAI multimodal content format)
# ---------------------------------------------------------------------------

def extract_images_from_content(content) -> tuple[str, List[str]]:
    """
    Parse an OpenAI message content value, which may be a plain string or a
    list of content parts (text / image_url).

    Returns (text_str, list_of_image_srcs) where each image src is either a
    data URI ("data:image/...;base64,...") or an https URL.
    """
    if isinstance(content, str):
        return content, []
    if not isinstance(content, list):
        return str(content), []

    text_parts: List[str] = []
    images: List[str] = []
    for part in content:
        part_type = part.get("type", "")
        if part_type == "text":
            text_parts.append(part.get("text", ""))
        elif part_type == "image_url":
            url = part.get("image_url", {}).get("url", "")
            if url:
                images.append(url)

    return " ".join(text_parts), images


def _load_image_bytes(src: str) -> bytes:
    """Fetch raw image bytes from a data URI or a URL."""
    if src.startswith("data:"):
        _, data = src.split(",", 1)
        return _base64.b64decode(data)
    with _urllib_request.urlopen(src, timeout=15) as resp:
        return resp.read()


def load_pil_image(src: str):
    """Load a PIL.Image from a data URI or URL. Requires Pillow."""
    if not _PIL_AVAILABLE:
        raise RuntimeError(
            "Pillow is required for image inputs with vLLM. "
            "Install it with: pip install Pillow"
        )
    return _PILImage.open(io.BytesIO(_load_image_bytes(src))).convert("RGB")


def image_src_to_base64(src: str) -> str:
    """Return a raw base64 string (no data URI prefix) for Ollama."""
    if src.startswith("data:"):
        return src.split(",", 1)[1]
    return _base64.b64encode(_load_image_bytes(src)).decode()


def get_or_create_vllm_engine(model: Model):
    """Get or create a vLLM engine for the given model"""
    model_name = model.name
    
    if model_name not in _vllm_engines:
        with _engines_lock:
            # Double-check after acquiring lock
            if model_name not in _vllm_engines:
                try:
                    # Get HuggingFace token from model config or environment
                    # vLLM reads HF_TOKEN from environment automatically
                    hf_token = model.huggingface_token.strip() if model.huggingface_token else None
                    if not hf_token:
                        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
                    
                    # Set token in environment for vLLM to use (vLLM reads HF_TOKEN automatically)
                    if hf_token:
                        os.environ['HF_TOKEN'] = hf_token
                        os.environ['HUGGINGFACE_TOKEN'] = hf_token
                        print(f"Using HuggingFace token for authentication")
                    else:
                        print(f"Warning: No HuggingFace token found. Set HF_TOKEN in .env file or model config.")
                    
                    print(f"Initializing vLLM engine for model: {model.model_path}")
                    # vLLM automatically reads HF_TOKEN from environment, don't pass token parameter
                    _vllm_engines[model_name] = LLM(
                        model=model.model_path,
                        trust_remote_code=True,
                        max_model_len=model.max_context_length,
                    )
                    print(f"Successfully initialized vLLM engine for {model_name}")
                except Exception as e:
                    error_msg = f"Failed to initialize vLLM engine for {model.model_path}: {str(e)}"
                    print(error_msg)
                    if "gated" in str(e).lower() or "401" in str(e) or "access" in str(e).lower():
                        error_msg += "\n\nTip: For gated models, you need to provide a HuggingFace token. "
                        error_msg += "Set it in the Model's 'huggingface_token' field in Django admin, "
                        error_msg += "or set the HF_TOKEN environment variable."
                    raise RuntimeError(error_msg) from e
    
    return _vllm_engines[model_name]


def get_or_create_vllm_embedding_engine(model: Model):
    """Get or create a vLLM embedding engine for the given model"""
    model_name = model.name
    
    if model_name not in _vllm_embedding_engines:
        with _engines_lock:
            # Double-check after acquiring lock
            if model_name not in _vllm_embedding_engines:
                try:
                    # Get HuggingFace token from model config or environment
                    hf_token = model.huggingface_token.strip() if model.huggingface_token else None
                    if not hf_token:
                        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')
                    
                    # Set token in environment for vLLM to use
                    if hf_token:
                        os.environ['HF_TOKEN'] = hf_token
                        os.environ['HUGGINGFACE_TOKEN'] = hf_token
                        print(f"Using HuggingFace token for authentication")
                    else:
                        print(f"Warning: No HuggingFace token found. Set HF_TOKEN in .env file or model config.")
                    
                    print(f"Initializing vLLM embedding engine for model: {model.model_path}")
                    # vLLM embedding models use task="embed"
                    _vllm_embedding_engines[model_name] = LLM(
                        model=model.model_path,
                        task="embed",
                        trust_remote_code=True,
                        max_model_len=model.max_context_length,
                        enforce_eager=True,
                    )
                    print(f"Successfully initialized vLLM embedding engine for {model_name}")
                except Exception as e:
                    error_msg = f"Failed to initialize vLLM embedding engine for {model.model_path}: {str(e)}"
                    print(error_msg)
                    if "gated" in str(e).lower() or "401" in str(e) or "access" in str(e).lower():
                        error_msg += "\n\nTip: For gated models, you need to provide a HuggingFace token. "
                        error_msg += "Set it in the Model's 'huggingface_token' field in Django admin, "
                        error_msg += "or set the HF_TOKEN environment variable."
                    raise RuntimeError(error_msg) from e
    
    return _vllm_embedding_engines[model_name]


def get_or_create_engine(model: Model) -> Union[Any, str]:
    """Get or create an engine for the given model based on provider and type"""
    if model.provider == 'vllm':
        if model.model_type == 'embedding':
            return get_or_create_vllm_embedding_engine(model)
        else:
            return get_or_create_vllm_engine(model)
    elif model.provider == 'ollama':
        # Ollama doesn't need engine initialization, return model identifier
        return model.model_path
    else:
        raise ValueError(f"Unknown provider: {model.provider}")


def generate_with_vllm(engine, prompt: str, sampling_params,
                       images: Optional[List[str]] = None) -> tuple[str, int, int]:
    """
    Generate text using vLLM engine.

    ``images`` is an optional list of image srcs (data URIs or URLs).  When
    provided the prompt and images are forwarded as multimodal input via
    vLLM's ``multi_modal_data`` mechanism.  The calling model must support
    vision inputs (e.g. LLaVA, InternVL, Qwen-VL …).
    """
    if images:
        pil_images = [load_pil_image(src) for src in images]
        multi_modal_data = {"image": pil_images[0] if len(pil_images) == 1 else pil_images}
        vllm_input = {"prompt": prompt, "multi_modal_data": multi_modal_data}
        outputs = engine.generate([vllm_input], sampling_params)
    else:
        outputs = engine.generate([prompt], sampling_params)

    if not outputs or not outputs[0].outputs:
        raise ValueError("No output generated")

    generated_text = outputs[0].outputs[0].text
    input_tokens = count_tokens_approximate(prompt)
    output_tokens = count_tokens_approximate(generated_text)

    return generated_text, input_tokens, output_tokens


def format_messages_for_ollama(messages: list, system_prompt: str = "") -> list:
    """
    Format OpenAI-style messages for the Ollama API.

    Message content may be a plain string or a list of content parts
    (text / image_url).  Images are extracted per-message and placed in
    Ollama's ``images`` field as raw base64 strings.
    """
    ollama_messages = []

    if system_prompt:
        ollama_messages.append({"role": "system", "content": system_prompt})

    for msg in messages:
        role = msg.get("role", "")
        if role not in ["system", "user", "assistant"]:
            continue

        text, image_srcs = extract_images_from_content(msg.get("content", ""))
        ollama_msg: Dict[str, Any] = {"role": role, "content": text}
        if image_srcs:
            ollama_msg["images"] = [image_src_to_base64(src) for src in image_srcs]
        ollama_messages.append(ollama_msg)

    return ollama_messages


def get_ollama_client(model: Model):
    """Get Ollama client for the model"""
    return ollama.Client(host=model.ollama_base_url or 'localhost:11434')


def generate_with_ollama(model: Model, prompt: str, temperature: float, max_tokens: int,
                         top_p: Optional[float] = None, top_k: Optional[int] = None,
                         min_p: Optional[float] = None, presence_penalty: Optional[float] = None,
                         repetition_penalty: Optional[float] = None, thinking: Optional[ThinkValue] = None,
                         messages: Optional[list] = None, system_prompt: str = "") -> tuple[str, str, int, int]:
    """Generate text using Ollama. Returns (content, reasoning, input_tokens, output_tokens)."""
    client = get_ollama_client(model)
    model_name = model.model_path
    
    # Format messages for Ollama
    if messages:
        ollama_messages = format_messages_for_ollama(messages, system_prompt)
    else:
        # Fallback to simple prompt format
        ollama_messages = [{"role": "user", "content": prompt}]
    
    # Build options dict
    options = {
        "temperature": float(temperature),
        "num_predict": int(max_tokens),
    }
    
    if top_p is not None and top_p != 1.0:
        options["top_p"] = float(top_p)
    if top_k is not None and top_k != -1:
        options["top_k"] = int(top_k)
    if min_p is not None and min_p != 0.0:
        options["min_p"] = float(min_p)
    if presence_penalty is not None and presence_penalty != 0.0:
        options["presence_penalty"] = float(presence_penalty)
    if repetition_penalty is not None and repetition_penalty != 1.0:
        options["repeat_penalty"] = float(repetition_penalty)
    
    try:
        chat_kwargs = dict(model=model_name, messages=ollama_messages, options=options)
        apply_think_to_chat_kwargs(chat_kwargs, thinking)
        response = client.chat(**chat_kwargs)
        
        if hasattr(response, 'message'):
            content, reasoning = extract_ollama_message_parts(response.message)
        else:
            content, reasoning = extract_ollama_message_parts(response.get("message", {}))

        if not content and not reasoning:
            raise ValueError("No content in Ollama response")
        
        input_tokens = count_tokens_approximate(prompt)
        output_tokens = count_tokens_approximate(content) + count_tokens_approximate(reasoning)
        
        return content, reasoning, input_tokens, output_tokens
    
    except Exception as e:
        error_str = str(e).lower()
        # Check if model not found (404 error)
        if 'not found' in error_str or '404' in error_str or 'status code: 404' in error_str:
            print(f"Model {model_name} not found. Attempting to pull...")
            try:
                # Pull the model
                client.pull(model_name)
                print(f"Successfully pulled model {model_name}. Retrying generation...")
                
                # Retry generation after pulling
                retry_kwargs = dict(model=model_name, messages=ollama_messages, options=options)
                apply_think_to_chat_kwargs(retry_kwargs, thinking)
                response = client.chat(**retry_kwargs)
                
                content, reasoning = extract_ollama_message_parts(
                    response.message if hasattr(response, 'message') else response.get("message", {})
                )
                if not content and not reasoning:
                    raise ValueError("No content in Ollama response")
                
                input_tokens = count_tokens_approximate(prompt)
                output_tokens = count_tokens_approximate(content) + count_tokens_approximate(reasoning)
                
                return content, reasoning, input_tokens, output_tokens
            except Exception as pull_error:
                raise RuntimeError(f"Ollama API error: Failed to pull model {model_name}: {str(pull_error)}") from pull_error
        else:
            raise RuntimeError(f"Ollama API error: {str(e)}") from e


def count_tokens_approximate(text: str) -> int:
    """Approximate token count (rough estimate: 1 token ≈ 4 characters)"""
    return len(text) // 4


def check_rate_limit(api_key: APIKey) -> tuple[bool, Optional[str]]:
    """
    Check if API key has exceeded rate limits.
    Returns (is_allowed, error_message)
    """
    if not api_key.is_active:
        return False, "API key is not active"
    
    now = timezone.now()
    minute_ago = now - timedelta(minutes=1)
    hour_ago = now - timedelta(hours=1)
    
    # Check requests per minute
    rpm_count = LLMRequest.objects.filter(
        api_key=api_key,
        created_at__gte=minute_ago
    ).count()
    
    if rpm_count >= api_key.rate_limit_per_minute:
        return False, f"Rate limit exceeded: {api_key.rate_limit_per_minute} requests per minute"
    
    # Check requests per hour
    rph_count = LLMRequest.objects.filter(
        api_key=api_key,
        created_at__gte=hour_ago
    ).count()
    
    if rph_count >= api_key.rate_limit_per_hour:
        return False, f"Rate limit exceeded: {api_key.rate_limit_per_hour} requests per hour"
    
    return True, None


def format_messages_for_prompt(messages: list, system_prompt: str = "") -> str:
    """
    Format OpenAI-style messages into a single prompt string.
    Handles system, user, and assistant messages. Message content may be a
    plain string or a list of content parts (text / image_url); only text
    parts are included in the prompt string.
    """
    parts = []

    if system_prompt:
        parts.append(f"System: {system_prompt}")

    for msg in messages:
        role = msg.get("role", "")
        text, _ = extract_images_from_content(msg.get("content", ""))

        if role == "system":
            parts.append(f"System: {text}")
        elif role == "user":
            parts.append(f"User: {text}")
        elif role == "assistant":
            parts.append(f"Assistant: {text}")

    return "\n\n".join(parts)


def embed_with_vllm(engine, texts: list[str]) -> tuple[list[list[float]], int]:
    """Generate embeddings using vLLM embedding engine"""
    if not texts:
        raise ValueError("Texts list cannot be empty")
    
    # Generate embeddings
    outputs = engine.embed(texts)
    
    if not outputs:
        raise ValueError("No embeddings generated")
    
    # Extract embeddings
    embeddings = []
    for output in outputs:
        if hasattr(output, 'outputs') and hasattr(output.outputs, 'embedding'):
            embeddings.append(output.outputs.embedding)
        else:
            raise ValueError("Invalid embedding output format")
    
    # Approximate token count (sum of all texts)
    total_tokens = sum(count_tokens_approximate(text) for text in texts)
    
    return embeddings, total_tokens


def embed_with_ollama(model: Model, texts: list[str]) -> tuple[list[list[float]], int]:
    """Generate embeddings using Ollama"""
    if not texts:
        raise ValueError("Texts list cannot be empty")
    
    client = get_ollama_client(model)
    model_name = model.model_path
    
    embeddings = []
    
    try:
        # Ollama embeddings API processes one text at a time
        for text in texts:
            response = client.embeddings(
                model=model_name,
                prompt=text
            )
            
            embedding = response.get('embedding', [])
            if not embedding:
                raise ValueError(f"No embedding returned for text: {text[:50]}...")
            
            embeddings.append(embedding)
        
        # Approximate token count (sum of all texts)
        total_tokens = sum(count_tokens_approximate(text) for text in texts)
        
        return embeddings, total_tokens
    
    except Exception as e:
        error_str = str(e).lower()
        # Check if model not found (404 error)
        if 'not found' in error_str or '404' in error_str or 'status code: 404' in error_str:
            print(f"Model {model_name} not found. Attempting to pull...")
            try:
                # Pull the model
                client.pull(model_name)
                print(f"Successfully pulled model {model_name}. Retrying embedding...")
                
                # Retry embedding after pulling
                embeddings = []
                for text in texts:
                    response = client.embeddings(
                        model=model_name,
                        prompt=text
                    )
                    
                    embedding = response.get('embedding', [])
                    if not embedding:
                        raise ValueError(f"No embedding returned for text: {text[:50]}...")
                    
                    embeddings.append(embedding)
                
                # Approximate token count (sum of all texts)
                total_tokens = sum(count_tokens_approximate(text) for text in texts)
                
                return embeddings, total_tokens
            except Exception as pull_error:
                raise RuntimeError(f"Ollama embedding error: Failed to pull model {model_name}: {str(pull_error)}") from pull_error
        else:
            raise RuntimeError(f"Ollama embedding error: {str(e)}") from e

