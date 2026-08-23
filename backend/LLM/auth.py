from functools import wraps

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import APIKey
from .utils import check_rate_limit, get_rate_limit_headers, get_retry_after_seconds


def get_api_key_from_request(request):
    """Extract API key from request headers (Authorization: Bearer <key>)"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def apply_rate_limit_headers(response, api_key):
    for header, value in get_rate_limit_headers(api_key).items():
        response[header] = value
    return response


def require_api_key(view_func):
    """Decorator to require and validate API key"""
    @wraps(view_func)
    @csrf_exempt
    def wrapper(request, *args, **kwargs):
        api_key_str = get_api_key_from_request(request)

        if not api_key_str:
            return JsonResponse({
                'error': {
                    'message': 'Missing API key. Provide it in Authorization header as: Bearer <key>',
                    'type': 'authentication_error',
                    'code': 'missing_api_key'
                }
            }, status=401)

        try:
            api_key = APIKey.objects.get(key=api_key_str)
        except APIKey.DoesNotExist:
            return JsonResponse({
                'error': {
                    'message': 'Invalid API key',
                    'type': 'authentication_error',
                    'code': 'invalid_api_key'
                }
            }, status=401)

        if not api_key.is_active:
            return JsonResponse({
                'error': {
                    'message': 'API key is not active',
                    'type': 'authentication_error',
                    'code': 'inactive_api_key'
                }
            }, status=403)

        is_allowed, error_msg = check_rate_limit(api_key)
        if not is_allowed:
            response = JsonResponse({
                'error': {
                    'message': error_msg,
                    'type': 'rate_limit_error',
                    'code': 'rate_limit_exceeded'
                }
            }, status=429)
            apply_rate_limit_headers(response, api_key)
            response['Retry-After'] = str(get_retry_after_seconds(api_key))
            return response

        request.api_key = api_key
        response = view_func(request, *args, **kwargs)
        return apply_rate_limit_headers(response, api_key)

    return wrapper
