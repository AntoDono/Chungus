import json
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import Model, LLMRequest
from .auth import require_api_key
from .utils import (
    get_or_create_engine,
    format_messages_for_prompt,
    generate_with_vllm,
    generate_with_ollama,
    count_tokens_approximate,
    format_messages_for_ollama,
    get_ollama_client,
    extract_images_from_content,
    embed_with_vllm,
    embed_with_ollama,
    resolve_think_value,
    think_value_for_storage,
    apply_think_to_chat_kwargs,
)

from vllm import SamplingParams


@require_api_key
@require_http_methods(["POST"])
def chat_completions(request):
    """
    OpenAI-compatible chat completions endpoint
    POST /v1/chat/completions
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': {
                'message': 'Invalid JSON in request body',
                'type': 'invalid_request_error',
                'code': 'invalid_json'
            }
        }, status=400)
    
    # Extract parameters
    model_name = data.get('model')
    messages = data.get('messages', [])
    stream = data.get('stream', False)
    temperature = data.get('temperature')
    max_tokens = data.get('max_tokens')
    top_p = data.get('top_p')
    top_k = data.get('top_k')
    min_p = data.get('min_p')
    presence_penalty = data.get('presence_penalty')
    repetition_penalty = data.get('repetition_penalty')
    thinking = data.get('thinking')  # default / low / medium / high / true / false
    reasoning_effort = data.get('reasoning_effort')  # OpenAI-compatible alias
    
    # Validate model
    try:
        model = Model.objects.get(name=model_name, is_active=True)
    except Model.DoesNotExist:
        return JsonResponse({
            'error': {
                'message': f'Model "{model_name}" not found or not active',
                'type': 'invalid_request_error',
                'code': 'model_not_found'
            }
        }, status=404)
    
    # Validate that model is a chat model
    if model.model_type != 'chat':
        return JsonResponse({
            'error': {
                'message': f'Model "{model_name}" is not a chat model',
                'type': 'invalid_request_error',
                'code': 'invalid_model_type'
            }
        }, status=400)
    
    # Validate messages
    if not messages or not isinstance(messages, list):
        return JsonResponse({
            'error': {
                'message': 'messages must be a non-empty array',
                'type': 'invalid_request_error',
                'code': 'invalid_messages'
            }
        }, status=400)
    
    # Use model defaults if not provided
    if temperature is None:
        temperature = model.default_temperature
    if max_tokens is None:
        max_tokens = model.default_max_tokens
    if top_p is None:
        top_p = model.default_top_p
    if top_k is None:
        top_k = model.default_top_k
    if min_p is None:
        min_p = model.default_min_p
    if presence_penalty is None:
        presence_penalty = model.default_presence_penalty
    if repetition_penalty is None:
        repetition_penalty = model.default_repetition_penalty

    try:
        think_value = resolve_think_value(thinking, reasoning_effort, model.thinking_mode)
    except ValueError as exc:
        return JsonResponse({
            'error': {
                'message': str(exc),
                'type': 'invalid_request_error',
                'code': 'invalid_thinking',
            }
        }, status=400)
    
    # Format prompt from messages; collect images from all message content parts.
    # Content may be a plain string or an OpenAI multimodal list.
    system_prompt = ""
    formatted_messages = []
    all_images = []
    for msg in messages:
        text, img_srcs = extract_images_from_content(msg.get('content', ''))
        all_images.extend(img_srcs)
        if msg.get('role') == 'system':
            system_prompt = text
        else:
            formatted_messages.append(msg)

    prompt = format_messages_for_prompt(formatted_messages, system_prompt)

    # Create LLMRequest record
    llm_request = LLMRequest.objects.create(
        api_key=request.api_key,
        model=model,
        prompt=prompt,
        system_prompt=system_prompt,
        images=all_images,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        top_k=top_k,
        min_p=min_p,
        presence_penalty=presence_penalty,
        repetition_penalty=repetition_penalty,
        thinking=think_value_for_storage(think_value),
        stream=stream,
        request_metadata={'messages': messages}
    )
    
    try:
        # Mark request as started
        llm_request.mark_started()
        
        # Calculate input tokens (approximate)
        input_tokens = count_tokens_approximate(prompt)
        
        # Route to appropriate provider
        if model.provider == 'vllm':
            # Get vLLM engine
            engine = get_or_create_engine(model)

            # Create sampling parameters
            sampling_params = SamplingParams(
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p if top_p is not None else 1.0,
                top_k=top_k if top_k is not None else -1,
                min_p=min_p if min_p is not None else 0.0,
                presence_penalty=presence_penalty if presence_penalty is not None else 0.0,
                repetition_penalty=repetition_penalty if repetition_penalty is not None else 1.0,
            )

            if stream:
                return stream_chat_completion(engine, sampling_params, llm_request, input_tokens, model, all_images)
            else:
                return generate_chat_completion_vllm(engine, sampling_params, llm_request, input_tokens, all_images)

        elif model.provider == 'ollama':
            # Images are embedded in formatted_messages and handled by format_messages_for_ollama
            if stream:
                return stream_chat_completion_ollama(model, llm_request, prompt, system_prompt, formatted_messages, temperature, max_tokens, top_p, top_k, min_p, presence_penalty, repetition_penalty, think_value, input_tokens)
            else:
                return generate_chat_completion_ollama(model, llm_request, prompt, system_prompt, formatted_messages, temperature, max_tokens, top_p, top_k, min_p, presence_penalty, repetition_penalty, think_value, input_tokens)
        
        else:
            raise ValueError(f"Unknown provider: {model.provider}")
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_message = str(e)
        
        # Log the full traceback for debugging (in production, use proper logging)
        print(f"Error in chat_completions: {error_message}")
        print(error_trace)
        
        llm_request.mark_failed(error_message)
        return JsonResponse({
            'error': {
                'message': f'Internal server error: {error_message}',
                'type': 'server_error',
                'code': 'internal_error'
            }
        }, status=500)


def generate_chat_completion_vllm(engine, sampling_params, llm_request, input_tokens, images=None):
    """Generate non-streaming chat completion using vLLM"""
    try:
        generated_text, input_tokens_actual, output_tokens = generate_with_vllm(
            engine, llm_request.prompt, sampling_params, images=images or []
        )
        
        # Mark as completed
        llm_request.mark_completed(
            response_text=generated_text,
            input_tokens=input_tokens_actual,
            output_tokens=output_tokens,
            metadata={'finish_reason': 'stop'}
        )
        
        # Format OpenAI-compatible response
        response_data = {
            'id': f'chatcmpl-{llm_request.id}',
            'object': 'chat.completion',
            'created': int(llm_request.created_at.timestamp()),
            'model': llm_request.model.name,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': generated_text
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': input_tokens_actual,
                'completion_tokens': output_tokens,
                'total_tokens': input_tokens_actual + output_tokens
            }
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        llm_request.mark_failed(str(e))
        raise


def generate_chat_completion_ollama(model, llm_request, prompt, system_prompt, messages, temperature, max_tokens, top_p, top_k, min_p, presence_penalty, repetition_penalty, thinking, input_tokens):
    """Generate non-streaming chat completion using Ollama"""
    try:
        generated_text, input_tokens_actual, output_tokens = generate_with_ollama(
            model, prompt, temperature, max_tokens, top_p, top_k, min_p, presence_penalty, repetition_penalty, thinking, messages, system_prompt
        )
        
        # Mark as completed
        llm_request.mark_completed(
            response_text=generated_text,
            input_tokens=input_tokens_actual,
            output_tokens=output_tokens,
            metadata={'finish_reason': 'stop'}
        )
        
        # Format OpenAI-compatible response
        response_data = {
            'id': f'chatcmpl-{llm_request.id}',
            'object': 'chat.completion',
            'created': int(llm_request.created_at.timestamp()),
            'model': llm_request.model.name,
            'choices': [{
                'index': 0,
                'message': {
                    'role': 'assistant',
                    'content': generated_text
                },
                'finish_reason': 'stop'
            }],
            'usage': {
                'prompt_tokens': input_tokens_actual,
                'completion_tokens': output_tokens,
                'total_tokens': input_tokens_actual + output_tokens
            }
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        llm_request.mark_failed(str(e))
        raise


def stream_chat_completion_ollama(model, llm_request, prompt, system_prompt, messages, temperature, max_tokens, top_p, top_k, min_p, presence_penalty, repetition_penalty, thinking, input_tokens):
    """Generate streaming chat completion using Ollama Python library"""
    def generate():
        try:
            
            client = get_ollama_client(model)
            model_name = model.model_path
            ollama_messages = format_messages_for_ollama(messages, system_prompt) if messages else [{"role": "user", "content": prompt}]
            
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
            
            accumulated_text = ""

            stream_kwargs = dict(model=model_name, messages=ollama_messages, options=options, stream=True)
            apply_think_to_chat_kwargs(stream_kwargs, thinking)

            # Stream response from Ollama
            stream = client.chat(**stream_kwargs)
            
            for chunk in stream:
                if hasattr(chunk, 'message'):
                    delta_content = chunk.message.content or ""
                else:
                    delta_content = chunk.get("message", {}).get("content", "")
                
                if delta_content:
                    accumulated_text += delta_content
                    chunk_response = {
                        'id': f'chatcmpl-{llm_request.id}',
                        'object': 'chat.completion.chunk',
                        'created': int(llm_request.created_at.timestamp()),
                        'model': llm_request.model.name,
                        'choices': [{
                            'index': 0,
                            'delta': {
                                'content': delta_content
                            },
                            'finish_reason': None
                        }]
                    }
                    yield f"data: {json.dumps(chunk_response)}\n\n"
                
                # Check if done
                if (hasattr(chunk, 'done') and chunk.done) or (not hasattr(chunk, 'done') and chunk.get("done", False)):
                    output_tokens = count_tokens_approximate(accumulated_text)
                    llm_request.mark_completed(
                        response_text=accumulated_text,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        metadata={'finish_reason': 'stop'}
                    )
                    
                    final_chunk = {
                        'id': f'chatcmpl-{llm_request.id}',
                        'object': 'chat.completion.chunk',
                        'created': int(llm_request.created_at.timestamp()),
                        'model': llm_request.model.name,
                        'choices': [{
                            'index': 0,
                            'delta': {},
                            'finish_reason': 'stop'
                        }],
                        'usage': {
                            'prompt_tokens': input_tokens,
                            'completion_tokens': output_tokens,
                            'total_tokens': input_tokens + output_tokens
                        }
                    }
                    yield f"data: {json.dumps(final_chunk)}\n\n"
                    break
            
            yield "data: [DONE]\n\n"
        
        except Exception as e:
            llm_request.mark_failed(str(e))
            error_chunk = {
                'error': {
                    'message': str(e),
                    'type': 'server_error',
                    'code': 'generation_error'
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    response = StreamingHttpResponse(
        generate(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


def stream_chat_completion(engine, sampling_params, llm_request, input_tokens, model, images=None):
    """Generate streaming chat completion using vLLM"""
    _images = images or []

    def generate():
        try:
            accumulated_text = ""

            if _images:
                from .utils import load_pil_image
                pil_images = [load_pil_image(src) for src in _images]
                multi_modal_data = {"image": pil_images[0] if len(pil_images) == 1 else pil_images}
                vllm_input = {"prompt": llm_request.prompt, "multi_modal_data": multi_modal_data}
                outputs = engine.generate([vllm_input], sampling_params)
            else:
                outputs = engine.generate([llm_request.prompt], sampling_params)
            
            if outputs and outputs[0].outputs:
                generated_text = outputs[0].outputs[0].text
                
                # Stream in chunks (simulate token-by-token streaming)
                # For true streaming, consider using AsyncLLMEngine with async views
                chunk_size = 5  # characters per chunk for smoother streaming
                for i in range(0, len(generated_text), chunk_size):
                    chunk_text = generated_text[i:i+chunk_size]
                    accumulated_text += chunk_text
                    
                    chunk = {
                        'id': f'chatcmpl-{llm_request.id}',
                        'object': 'chat.completion.chunk',
                        'created': int(llm_request.created_at.timestamp()),
                        'model': llm_request.model.name,
                        'choices': [{
                            'index': 0,
                            'delta': {
                                'content': chunk_text
                            },
                            'finish_reason': None
                        }]
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Final chunk with finish reason
                output_tokens = count_tokens_approximate(accumulated_text)
                llm_request.mark_completed(
                    response_text=accumulated_text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    metadata={'finish_reason': 'stop'}
                )
                
                final_chunk = {
                    'id': f'chatcmpl-{llm_request.id}',
                    'object': 'chat.completion.chunk',
                    'created': int(llm_request.created_at.timestamp()),
                    'model': llm_request.model.name,
                    'choices': [{
                        'index': 0,
                        'delta': {},
                        'finish_reason': 'stop'
                    }],
                    'usage': {
                        'prompt_tokens': input_tokens,
                        'completion_tokens': output_tokens,
                        'total_tokens': input_tokens + output_tokens
                    }
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
            else:
                raise ValueError("No output generated")
            
            yield "data: [DONE]\n\n"
        
        except Exception as e:
            llm_request.mark_failed(str(e))
            error_chunk = {
                'error': {
                    'message': str(e),
                    'type': 'server_error',
                    'code': 'generation_error'
                }
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"
    
    response = StreamingHttpResponse(
        generate(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@require_api_key
@require_http_methods(["GET"])
def list_models(request):
    """
    List available models
    GET /v1/models
    """
    models = Model.objects.filter(is_active=True)
    models_data = {
        'object': 'list',
        'data': [
            {
                'id': model.name,
                'object': 'model',
                'created': int(model.created_at.timestamp()),
                'owned_by': 'chungus',
                'permission': [],
                'root': model.name,
                'parent': None
            }
            for model in models
        ]
    }
    return JsonResponse(models_data)


@require_api_key
@require_http_methods(["POST"])
def embeddings(request):
    """
    OpenAI-compatible embeddings endpoint
    POST /v1/embeddings
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'error': {
                'message': 'Invalid JSON in request body',
                'type': 'invalid_request_error',
                'code': 'invalid_json'
            }
        }, status=400)
    
    # Extract parameters
    model_name = data.get('model')
    input_data = data.get('input')
    
    # Validate model
    try:
        model = Model.objects.get(name=model_name, is_active=True)
    except Model.DoesNotExist:
        return JsonResponse({
            'error': {
                'message': f'Model "{model_name}" not found or not active',
                'type': 'invalid_request_error',
                'code': 'model_not_found'
            }
        }, status=404)
    
    # Validate that model is an embedding model
    if model.model_type != 'embedding':
        return JsonResponse({
            'error': {
                'message': f'Model "{model_name}" is not an embedding model',
                'type': 'invalid_request_error',
                'code': 'invalid_model_type'
            }
        }, status=400)
    
    # Validate input
    if input_data is None:
        return JsonResponse({
            'error': {
                'message': 'input is required',
                'type': 'invalid_request_error',
                'code': 'missing_input'
            }
        }, status=400)
    
    # Handle both string and array inputs
    if isinstance(input_data, str):
        texts = [input_data]
    elif isinstance(input_data, list):
        if not input_data:
            return JsonResponse({
                'error': {
                    'message': 'input array cannot be empty',
                    'type': 'invalid_request_error',
                    'code': 'empty_input'
                }
            }, status=400)
        texts = input_data
    else:
        return JsonResponse({
            'error': {
                'message': 'input must be a string or array of strings',
                'type': 'invalid_request_error',
                'code': 'invalid_input_type'
            }
        }, status=400)
    
    # Validate all items in array are strings
    for i, text in enumerate(texts):
        if not isinstance(text, str):
            return JsonResponse({
                'error': {
                    'message': f'input[{i}] must be a string',
                    'type': 'invalid_request_error',
                    'code': 'invalid_input_type'
                }
            }, status=400)
    
    # Create the input string for logging (join all texts)
    input_text = '\n'.join(texts) if isinstance(input_data, list) else input_data
    
    # Create LLMRequest record
    llm_request = LLMRequest.objects.create(
        api_key=request.api_key,
        model=model,
        prompt=input_text,
        system_prompt="",
        temperature=None,
        max_tokens=None,
        stream=False,
        request_metadata={'input': input_data, 'type': 'embedding'}
    )
    
    try:
        # Mark request as started
        llm_request.mark_started()
        
        # Route to appropriate provider
        if model.provider == 'vllm':
            engine = get_or_create_engine(model)
            embeddings_list, total_tokens = embed_with_vllm(engine, texts)
        elif model.provider == 'ollama':
            embeddings_list, total_tokens = embed_with_ollama(model, texts)
        else:
            raise ValueError(f"Unknown provider: {model.provider}")
        
        # Calculate output tokens as embedding dimensions
        embedding_dimensions = len(embeddings_list[0]) if embeddings_list and len(embeddings_list) > 0 else 0
        output_tokens = embedding_dimensions * len(embeddings_list)  # Total embedding values
        
        # Mark as completed with token usage
        llm_request.mark_completed(
            response_text=f"Generated {len(embeddings_list)} embeddings",
            input_tokens=total_tokens,
            output_tokens=output_tokens,
            metadata={'num_embeddings': len(embeddings_list), 'embedding_dimensions': embedding_dimensions}
        )
        
        # Format OpenAI-compatible response
        response_data = {
            'object': 'list',
            'data': [
                {
                    'object': 'embedding',
                    'index': i,
                    'embedding': embedding
                }
                for i, embedding in enumerate(embeddings_list)
            ],
            'model': model.name,
            'usage': {
                'prompt_tokens': total_tokens,
                'total_tokens': total_tokens
            }
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        error_message = str(e)
        
        # Log the full traceback for debugging
        print(f"Error in embeddings: {error_message}")
        print(error_trace)
        
        # Mark request as failed if it exists
        if 'llm_request' in locals():
            llm_request.mark_failed(error_message)
        
        return JsonResponse({
            'error': {
                'message': f'Internal server error: {error_message}',
                'type': 'server_error',
                'code': 'internal_error'
            }
        }, status=500)
