"""
Management command to warm up models marked with alwayswarm=True.
Sends a simple "what is 1 + 1" request to keep models from going cold.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from LLM.models import Model, APIKey, LLMRequest
from LLM.utils import (
    get_or_create_engine,
    generate_with_vllm,
    generate_with_ollama,
    format_messages_for_ollama,
    count_tokens_approximate,
    format_messages_for_prompt
)
from vllm import SamplingParams


class Command(BaseCommand):
    help = 'Warm up models with alwayswarm=True by sending a simple request'

    def handle(self, *args, **options):
        # Get all active models with alwayswarm=True
        models_to_warm = Model.objects.filter(alwayswarm=True, is_active=True)
        
        if not models_to_warm.exists():
            self.stdout.write(self.style.SUCCESS('No models to warm up.'))
            return
        
        # Get or create a system API key for warmup requests
        # We'll use the first active API key, or create a system one
        try:
            api_key = APIKey.objects.filter(is_active=True).first()
            if not api_key:
                self.stdout.write(self.style.WARNING('No active API keys found. Skipping warmup.'))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting API key: {e}'))
            return
        
        warmup_prompt = "what is 1 + 1"
        messages = [{"role": "user", "content": warmup_prompt}]
        
        for model in models_to_warm:
            try:
                self.stdout.write(f'Warming up model: {model.name}...')
                
                # Create a minimal LLMRequest record (optional, for tracking)
                llm_request = LLMRequest.objects.create(
                    api_key=api_key,
                    model=model,
                    prompt=warmup_prompt,
                    system_prompt="",
                    temperature=model.default_temperature,
                    max_tokens=10,  # Very short response
                    stream=False,
                    request_metadata={'warmup': True}
                )
                
                llm_request.mark_started()
                input_tokens = count_tokens_approximate(warmup_prompt)
                
                # Route to appropriate provider
                if model.provider == 'vllm':
                    engine = get_or_create_engine(model)
                    sampling_params = SamplingParams(
                        temperature=model.default_temperature,
                        max_tokens=10,
                        top_p=1.0,
                        top_k=-1,
                    )
                    generated_text, input_tokens_actual, output_tokens = generate_with_vllm(
                        engine, warmup_prompt, sampling_params
                    )
                    
                elif model.provider == 'ollama':
                    formatted_messages = format_messages_for_ollama(messages, "")
                    generated_text, input_tokens_actual, output_tokens = generate_with_ollama(
                        model, warmup_prompt, model.default_temperature, 10,
                        None, None, formatted_messages, ""
                    )
                else:
                    raise ValueError(f"Unknown provider: {model.provider}")
                
                # Mark as completed
                llm_request.mark_completed(
                    response_text=generated_text,
                    input_tokens=input_tokens_actual,
                    output_tokens=output_tokens,
                    metadata={'warmup': True, 'finish_reason': 'stop'}
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully warmed up {model.name}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'✗ Error warming up {model.name}: {e}')
                )
                # Mark request as failed if it exists
                if 'llm_request' in locals():
                    try:
                        llm_request.mark_failed(str(e))
                    except:
                        pass
        
        self.stdout.write(self.style.SUCCESS('Warmup complete.'))

