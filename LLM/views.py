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
    get_ollama_client
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
    
    # Format prompt from messages
    system_prompt = ""
    formatted_messages = []
    for msg in messages:
        if msg.get('role') == 'system':
            system_prompt = msg.get('content', '')
        else:
            formatted_messages.append(msg)
    
    prompt = format_messages_for_prompt(formatted_messages, system_prompt)
    
    # Create LLMRequest record
    llm_request = LLMRequest.objects.create(
        api_key=request.api_key,
        model=model,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        top_k=top_k,
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
            )
            
            if stream:
                # Streaming response
                return stream_chat_completion(engine, sampling_params, llm_request, input_tokens, model)
            else:
                # Non-streaming response
                return generate_chat_completion_vllm(engine, sampling_params, llm_request, input_tokens)
        
        elif model.provider == 'ollama':
            if stream:
                # Streaming response for Ollama
                return stream_chat_completion_ollama(model, llm_request, prompt, system_prompt, formatted_messages, temperature, max_tokens, top_p, top_k, input_tokens)
            else:
                # Non-streaming response for Ollama
                return generate_chat_completion_ollama(model, llm_request, prompt, system_prompt, formatted_messages, temperature, max_tokens, top_p, top_k, input_tokens)
        
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


def generate_chat_completion_vllm(engine, sampling_params, llm_request, input_tokens):
    """Generate non-streaming chat completion using vLLM"""
    try:
        # Generate response using vLLM
        generated_text, input_tokens_actual, output_tokens = generate_with_vllm(
            engine, llm_request.prompt, sampling_params
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


def generate_chat_completion_ollama(model, llm_request, prompt, system_prompt, messages, temperature, max_tokens, top_p, top_k, input_tokens):
    """Generate non-streaming chat completion using Ollama"""
    try:
        generated_text, input_tokens_actual, output_tokens = generate_with_ollama(
            model, prompt, temperature, max_tokens, top_p, top_k, messages, system_prompt
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


def stream_chat_completion_ollama(model, llm_request, prompt, system_prompt, messages, temperature, max_tokens, top_p, top_k, input_tokens):
    """Generate streaming chat completion using Ollama Python library"""
    def generate():
        try:
            
            client = get_ollama_client(model)
            model_name = model.model_path
            ollama_messages = format_messages_for_ollama(messages, system_prompt) if messages else [{"role": "user", "content": prompt}]
            
            # Build options dict
            options = {
                "temperature": temperature,
                "num_predict": max_tokens,
            }
            
            if top_p is not None:
                options["top_p"] = top_p
            if top_k is not None:
                options["top_k"] = top_k
            
            accumulated_text = ""
            
            # Stream response from Ollama
            stream = client.chat(
                model=model_name,
                messages=ollama_messages,
                options=options,
                stream=True
            )
            
            for chunk in stream:
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
                if chunk.get("done", False):
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


def stream_chat_completion(engine, sampling_params, llm_request, input_tokens, model):
    """Generate streaming chat completion using vLLM"""
    def generate():
        try:
            accumulated_text = ""
            
            # Generate with streaming - vLLM supports streaming via generate_stream
            # For now, we'll simulate streaming by generating and chunking
            # In production, you'd use AsyncLLMEngine for true streaming
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
