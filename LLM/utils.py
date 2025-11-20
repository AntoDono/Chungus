from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Count
from .models import APIKey, Model, LLMRequest
from typing import Optional, Dict, Union, Any
import threading
import os
import json

from vllm import LLM, SamplingParams
import ollama


# Global engine cache - one engine per model
_vllm_engines: Dict[str, Any] = {}
_vllm_embedding_engines: Dict[str, Any] = {}
_engines_lock = threading.Lock()


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


def generate_with_vllm(engine, prompt: str, sampling_params) -> tuple[str, int, int]:
    """Generate text using vLLM engine"""
    outputs = engine.generate([prompt], sampling_params)
    
    if not outputs or not outputs[0].outputs:
        raise ValueError("No output generated")
    
    generated_text = outputs[0].outputs[0].text
    # Approximate token counts
    input_tokens = count_tokens_approximate(prompt)
    output_tokens = count_tokens_approximate(generated_text)
    
    return generated_text, input_tokens, output_tokens


def format_messages_for_ollama(messages: list, system_prompt: str = "") -> list:
    """Format OpenAI-style messages for Ollama API"""
    ollama_messages = []
    
    # Add system message if present
    if system_prompt:
        ollama_messages.append({"role": "system", "content": system_prompt})
    
    # Convert OpenAI messages to Ollama format
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role in ["system", "user", "assistant"]:
            ollama_messages.append({"role": role, "content": content})
    
    return ollama_messages


def get_ollama_client(model: Model):
    """Get Ollama client for the model"""
    return ollama.Client(host=model.ollama_base_url or 'localhost:11434')


def generate_with_ollama(model: Model, prompt: str, temperature: float, max_tokens: int, 
                         top_p: Optional[float] = None, top_k: Optional[int] = None,
                         messages: Optional[list] = None, system_prompt: str = "") -> tuple[str, int, int]:
    """Generate text using Ollama Python library"""
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
        "temperature": temperature,
        "num_predict": max_tokens,
    }
    
    if top_p is not None:
        options["top_p"] = top_p
    if top_k is not None:
        options["top_k"] = top_k
    
    try:
        response = client.chat(
            model=model_name,
            messages=ollama_messages,
            options=options
        )
        
        generated_text = response.get("message", {}).get("content", "")
        if not generated_text:
            raise ValueError("No content in Ollama response")
        
        # Approximate token counts
        input_tokens = count_tokens_approximate(prompt)
        output_tokens = count_tokens_approximate(generated_text)
        
        return generated_text, input_tokens, output_tokens
    
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
                response = client.chat(
                    model=model_name,
                    messages=ollama_messages,
                    options=options
                )
                
                generated_text = response.get("message", {}).get("content", "")
                if not generated_text:
                    raise ValueError("No content in Ollama response")
                
                # Approximate token counts
                input_tokens = count_tokens_approximate(prompt)
                output_tokens = count_tokens_approximate(generated_text)
                
                return generated_text, input_tokens, output_tokens
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
    Handles system, user, and assistant messages.
    """
    parts = []
    
    if system_prompt:
        parts.append(f"System: {system_prompt}")
    
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    
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

