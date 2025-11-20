from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
import json
from LLM.models import Model, APIKey, LLMRequest
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count


def superuser_required(user):
    """Check if user is a superuser"""
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(superuser_required)
@require_http_methods(["GET"])
def get_models(request):
    """Get all models"""
    models = Model.objects.all().order_by('-created_at')
    return JsonResponse({
        'models': [
            {
                'id': m.id,
                'name': m.name,
                'description': m.description,
                'model_path': m.model_path,
                'provider': m.provider,
                'is_active': m.is_active,
                'max_context_length': m.max_context_length,
                'default_temperature': m.default_temperature,
                'default_max_tokens': m.default_max_tokens,
                'total_requests': m.total_requests,
                'total_responses': m.total_responses,
                'total_errors': m.total_errors,
                'total_tokens_processed': m.total_tokens_processed,
                'created_at': m.created_at.isoformat(),
            }
            for m in models
        ]
    })


@login_required
@user_passes_test(superuser_required)
@csrf_exempt
@require_http_methods(["POST"])
def create_model(request):
    """Create a new model"""
    try:
        data = json.loads(request.body)
        model = Model.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            model_path=data['model_path'],
            provider=data.get('provider', 'vllm'),
            is_active=data.get('is_active', True),
            max_context_length=data.get('max_context_length', 4096),
            default_temperature=data.get('default_temperature', 0.7),
            default_max_tokens=data.get('default_max_tokens', 512),
            huggingface_token=data.get('huggingface_token', ''),
            ollama_base_url=data.get('ollama_base_url', 'http://localhost:11434'),
        )
        return JsonResponse({'success': True, 'model_id': model.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(superuser_required)
@csrf_exempt
@require_http_methods(["POST"])
def update_model(request, model_id):
    """Update a model"""
    try:
        data = json.loads(request.body)
        model = Model.objects.get(id=model_id)
        
        if 'name' in data:
            model.name = data['name']
        if 'description' in data:
            model.description = data['description']
        if 'model_path' in data:
            model.model_path = data['model_path']
        if 'provider' in data:
            model.provider = data['provider']
        if 'is_active' in data:
            model.is_active = data['is_active']
        if 'max_context_length' in data:
            model.max_context_length = data['max_context_length']
        if 'default_temperature' in data:
            model.default_temperature = data['default_temperature']
        if 'default_max_tokens' in data:
            model.default_max_tokens = data['default_max_tokens']
        if 'huggingface_token' in data:
            model.huggingface_token = data['huggingface_token']
        if 'ollama_base_url' in data:
            model.ollama_base_url = data['ollama_base_url']
        
        model.save()
        return JsonResponse({'success': True})
    except Model.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Model not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(superuser_required)
@csrf_exempt
@require_http_methods(["POST"])
def delete_model(request, model_id):
    """Delete a model"""
    try:
        model = Model.objects.get(id=model_id)
        model.delete()
        return JsonResponse({'success': True})
    except Model.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Model not found'}, status=404)


@login_required
@user_passes_test(superuser_required)
@require_http_methods(["GET"])
def get_api_keys(request):
    """Get all API keys"""
    api_keys = APIKey.objects.all().order_by('-created_at')
    return JsonResponse({
        'api_keys': [
            {
                'id': k.id,
                'name': k.name,
                'description': k.description,
                'key': k.key[:8] + '...' if len(k.key) > 8 else k.key,
                'is_active': k.is_active,
                'rate_limit_per_minute': k.rate_limit_per_minute,
                'rate_limit_per_hour': k.rate_limit_per_hour,
                'total_requests': k.total_requests,
                'total_tokens_processed': k.total_tokens_processed,
                'last_used_at': k.last_used_at.isoformat() if k.last_used_at else None,
                'created_at': k.created_at.isoformat(),
            }
            for k in api_keys
        ]
    })


@login_required
@user_passes_test(superuser_required)
@csrf_exempt
@require_http_methods(["POST"])
def create_api_key(request):
    """Create a new API key"""
    try:
        data = json.loads(request.body)
        api_key = APIKey.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            is_active=data.get('is_active', True),
            rate_limit_per_minute=data.get('rate_limit_per_minute', 60),
            rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
        )
        return JsonResponse({
            'success': True,
            'api_key_id': api_key.id,
            'key': api_key.key  # Return full key only on creation
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(superuser_required)
@csrf_exempt
@require_http_methods(["POST"])
def update_api_key(request, api_key_id):
    """Update an API key"""
    try:
        data = json.loads(request.body)
        api_key = APIKey.objects.get(id=api_key_id)
        
        if 'name' in data:
            api_key.name = data['name']
        if 'description' in data:
            api_key.description = data['description']
        if 'is_active' in data:
            api_key.is_active = data['is_active']
        if 'rate_limit_per_minute' in data:
            api_key.rate_limit_per_minute = data['rate_limit_per_minute']
        if 'rate_limit_per_hour' in data:
            api_key.rate_limit_per_hour = data['rate_limit_per_hour']
        
        api_key.save()
        return JsonResponse({'success': True})
    except APIKey.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'API key not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@user_passes_test(superuser_required)
@csrf_exempt
@require_http_methods(["POST"])
def delete_api_key(request, api_key_id):
    """Delete an API key"""
    try:
        api_key = APIKey.objects.get(id=api_key_id)
        api_key.delete()
        return JsonResponse({'success': True})
    except APIKey.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'API key not found'}, status=404)


@login_required
@user_passes_test(superuser_required)
@require_http_methods(["GET"])
def get_api_key_full(request, api_key_id):
    """Get the full API key (for reveal functionality)"""
    try:
        api_key = APIKey.objects.get(id=api_key_id)
        return JsonResponse({
            'success': True,
            'key': api_key.key
        })
    except APIKey.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'API key not found'}, status=404)


from django.db.models import Q

from django.db.models import Q
from django.db.models.functions import TruncHour

@login_required
@user_passes_test(superuser_required)
@require_http_methods(["GET"])
def get_chart_data(request):
    """Get chart data for dashboard"""
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    # Hourly request counts using TruncHour
    try:
        hourly_data = LLMRequest.objects.filter(
            created_at__gte=last_24h
        ).annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
    except:
        # Fallback for databases that don't support TruncHour
        requests = list(LLMRequest.objects.filter(created_at__gte=last_24h).values('created_at'))
        hourly_counts = {}
        for req in requests:
            hour = req['created_at'].replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour.isoformat()] = hourly_counts.get(hour.isoformat(), 0) + 1
        hourly_data = [{'hour': k, 'count': v} for k, v in sorted(hourly_counts.items())]
    
    # Model usage
    model_usage = Model.objects.annotate(
        request_count=Count('requests', filter=Q(requests__created_at__gte=last_24h))
    ).filter(request_count__gt=0).values('name', 'request_count')
    
    return JsonResponse({
        'hourly_requests': list(hourly_data),
        'model_usage': list(model_usage),
    })

