import json
import time
from datetime import timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce, TruncHour
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .gpu import gpu_status
from .models import APIKey, LLMRequest, Model, UserAPIKey
from .session_auth import require_admin, require_session, user_payload
from .session_auth import GROUP_ADMIN, GROUP_USER, get_user_role, is_admin_user, set_user_role
from .utils import get_usage_window_counts

_PROCESS_STARTED = time.monotonic()


MODEL_BODY_FIELDS = (
    'name',
    'description',
    'model_path',
    'model_type',
    'provider',
    'is_active',
    'is_default',
    'alwayswarm',
    'thinking_mode',
    'ollama_base_url',
    'huggingface_token',
    'max_context_length',
    'default_temperature',
    'default_max_tokens',
    'default_top_p',
    'default_top_k',
    'default_min_p',
    'default_presence_penalty',
    'default_repetition_penalty',
)


def _json_body(request):
    try:
        if not request.body:
            return {}
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def _error(message, status=400, code='invalid_request', error_type='invalid_request_error'):
    return JsonResponse({
        'error': {
            'message': message,
            'type': error_type,
            'code': code,
        }
    }, status=status)


def _key_preview(key):
    if not key:
        return ''
    return f'{key[:8]}...' if len(key) > 8 else key


def _owned_keys_qs(user):
    return APIKey.objects.filter(owner_mapping__user=user)


def _serialize_key(api_key, now=None, include_owner=False):
    now = now or timezone.now()
    counts = get_usage_window_counts([api_key.id], now=now)
    payload = {
        'id': api_key.id,
        'name': api_key.name,
        'description': api_key.description,
        'key_preview': _key_preview(api_key.key),
        'is_active': api_key.is_active,
        'rate_limit_per_minute': api_key.rate_limit_per_minute,
        'rate_limit_per_hour': api_key.rate_limit_per_hour,
        'total_requests': api_key.total_requests,
        'total_tokens_processed': api_key.total_tokens_processed,
        'last_used_at': api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        'requests_this_minute': counts['minute'],
        'requests_this_hour': counts['hour'],
    }
    if include_owner:
        mapping = getattr(api_key, 'owner_mapping', None)
        payload['user_id'] = mapping.user_id if mapping else None
        payload['username'] = mapping.user.username if mapping else None
    return payload


def _serialize_model(model):
    return {
        'id': model.id,
        'name': model.name,
        'description': model.description,
        'model_path': model.model_path,
        'model_type': model.model_type,
        'provider': model.provider,
        'is_active': model.is_active,
        'is_default': model.is_default,
        'alwayswarm': model.alwayswarm,
        'thinking_mode': model.thinking_mode,
        'ollama_base_url': model.ollama_base_url,
        'huggingface_token': model.huggingface_token,
        'max_context_length': model.max_context_length,
        'default_temperature': model.default_temperature,
        'default_max_tokens': model.default_max_tokens,
        'default_top_p': model.default_top_p,
        'default_top_k': model.default_top_k,
        'default_min_p': model.default_min_p,
        'default_presence_penalty': model.default_presence_penalty,
        'default_repetition_penalty': model.default_repetition_penalty,
        'total_requests': model.total_requests,
        'total_responses': model.total_responses,
        'total_errors': model.total_errors,
        'total_tokens_processed': model.total_tokens_processed,
        'created_at': model.created_at.isoformat(),
    }


def _apply_model_fields(model, data):
    for field in MODEL_BODY_FIELDS:
        if field in data:
            setattr(model, field, data[field])


def _set_key_owner(api_key, user_id):
    if user_id in (None, '', False):
        UserAPIKey.objects.filter(api_key=api_key).delete()
        return
    try:
        user = User.objects.get(id=int(user_id))
    except (User.DoesNotExist, TypeError, ValueError):
        raise ValueError('Invalid user_id')
    mapping, created = UserAPIKey.objects.get_or_create(
        api_key=api_key,
        defaults={'user': user},
    )
    if not created and mapping.user_id != user.id:
        mapping.user = user
        mapping.save(update_fields=['user'])


def _user_can_access_key(user, api_key):
    if is_admin_user(user):
        return True
    return UserAPIKey.objects.filter(user=user, api_key=api_key).exists()


def _serialize_request_row(req):
    return {
        'id': req.id,
        'model_name': req.model.name,
        'api_key_name': req.api_key.name,
        'api_key_id': req.api_key_id,
        'status': req.status,
        'input_tokens': req.input_tokens,
        'output_tokens': req.output_tokens,
        'total_tokens': req.total_tokens,
        'created_at': req.created_at.isoformat(),
        'completed_at': req.completed_at.isoformat() if req.completed_at else None,
        'error_message': req.error_message if req.status == 'failed' else None,
    }


def _paginate_requests(queryset, request):
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 50))
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    return JsonResponse({
        'requests': [_serialize_request_row(req) for req in page_obj],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
    })


def _hour_key(dt):
    if timezone.is_aware(dt):
        dt = timezone.localtime(dt)
    return dt.replace(minute=0, second=0, microsecond=0)


def hourly_request_series(hours=24):
    now = _hour_key(timezone.now())
    start = now - timedelta(hours=hours - 1)
    try:
        rows = (
            LLMRequest.objects.filter(created_at__gte=start)
            .annotate(bucket=TruncHour('created_at'))
            .values('bucket')
            .annotate(count=Count('id'), tokens=Coalesce(Sum('total_tokens'), 0))
            .order_by('bucket')
        )
        by_hour = {}
        for row in rows:
            if not row['bucket']:
                continue
            by_hour[_hour_key(row['bucket'])] = {
                'count': row['count'] or 0,
                'tokens': row['tokens'] or 0,
            }
    except Exception:
        by_hour = {}
        for created_at in LLMRequest.objects.filter(created_at__gte=start).values_list('created_at', 'total_tokens'):
            key = _hour_key(created_at[0])
            slot = by_hour.setdefault(key, {'count': 0, 'tokens': 0})
            slot['count'] += 1
            slot['tokens'] += created_at[1] or 0

    series = []
    cursor = start
    for _ in range(hours):
        hit = by_hour.get(cursor, {'count': 0, 'tokens': 0})
        series.append({
            'hour': cursor.isoformat(),
            'count': hit['count'],
            'tokens': hit['tokens'],
        })
        cursor += timedelta(hours=1)
    return series


@require_GET
def health(request):
    return JsonResponse({
        'status': 'ok',
        'uptime_seconds': int(time.monotonic() - _PROCESS_STARTED),
    })


@require_GET
def public_stats(request):
    token_stats = LLMRequest.objects.aggregate(total_tokens=Sum('total_tokens'))
    last_24h = timezone.now() - timedelta(hours=24)
    return JsonResponse({
        'total_requests': LLMRequest.objects.count(),
        'total_tokens': token_stats.get('total_tokens') or 0,
        'requests_24h': LLMRequest.objects.filter(created_at__gte=last_24h).count(),
        'hourly_requests': hourly_request_series(),
    })


@require_GET
def public_gpu(request):
    return JsonResponse(gpu_status())


@require_GET
@ensure_csrf_cookie
def auth_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@require_POST
def auth_login(request):
    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    user = authenticate(request, username=username, password=password)
    if user is None:
        return _error(
            'Invalid username or password',
            status=401,
            code='invalid_credentials',
            error_type='authentication_error',
        )
    if not user.is_active:
        return _error(
            'Account is deactivated',
            status=401,
            code='inactive_user',
            error_type='authentication_error',
        )
    login(request, user)
    return JsonResponse({'user': user_payload(user)})


@require_POST
def auth_logout(request):
    logout(request)
    return JsonResponse({'success': True})


@require_GET
@require_session
def auth_me(request):
    return JsonResponse(user_payload(request.user))


@require_GET
@require_session
def me_keys(request):
    now = timezone.now()
    keys = _owned_keys_qs(request.user).select_related('owner_mapping').order_by('-created_at')
    return JsonResponse({
        'keys': [_serialize_key(k, now=now) for k in keys],
    })


@require_GET
@require_session
def me_key_full(request, key_id):
    try:
        api_key = APIKey.objects.get(id=key_id)
    except APIKey.DoesNotExist:
        return _error('API key not found', status=404, code='not_found')
    if not _user_can_access_key(request.user, api_key):
        return _error('Forbidden', status=403, code='forbidden', error_type='authorization_error')
    return JsonResponse({'key': api_key.key})


@require_GET
@require_session
def me_usage(request):
    now = timezone.now()
    keys = list(_owned_keys_qs(request.user).order_by('-created_at'))
    key_ids = [k.id for k in keys]
    totals = LLMRequest.objects.filter(api_key_id__in=key_ids).aggregate(
        total_requests=Count('id'),
        total_tokens=Sum('total_tokens'),
    )
    windows = get_usage_window_counts(key_ids, now=now) if key_ids else {'minute': 0, 'hour': 0, 'day': 0}
    return JsonResponse({
        'total_requests': totals.get('total_requests') or 0,
        'total_tokens': totals.get('total_tokens') or 0,
        'requests_24h': windows['day'],
        'requests_this_minute': windows['minute'],
        'requests_this_hour': windows['hour'],
        'keys': [_serialize_key(k, now=now) for k in keys],
    })


@require_GET
@require_session
def me_requests(request):
    key_ids = list(_owned_keys_qs(request.user).values_list('id', flat=True))
    queryset = (
        LLMRequest.objects.filter(api_key_id__in=key_ids)
        .select_related('model', 'api_key')
        .order_by('-created_at')
    )
    return _paginate_requests(queryset, request)


@require_http_methods(['GET', 'POST'])
@require_admin
def admin_models(request):
    if request.method == 'GET':
        models = Model.objects.all().order_by('-created_at')
        return JsonResponse({'models': [_serialize_model(m) for m in models]})

    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    if not data.get('name') or not data.get('model_path'):
        return _error('name and model_path are required')
    model = Model()
    _apply_model_fields(model, data)
    try:
        model.save()
    except Exception as exc:
        return _error(str(exc))
    return JsonResponse({'success': True, 'model_id': model.id, 'model': _serialize_model(model)})


@require_POST
@require_admin
def admin_model_update(request, model_id):
    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return _error('Model not found', status=404, code='not_found')
    _apply_model_fields(model, data)
    try:
        model.save()
    except Exception as exc:
        return _error(str(exc))
    return JsonResponse({'success': True, 'model': _serialize_model(model)})


@require_POST
@require_admin
def admin_model_delete(request, model_id):
    try:
        model = Model.objects.get(id=model_id)
    except Model.DoesNotExist:
        return _error('Model not found', status=404, code='not_found')
    model.delete()
    return JsonResponse({'success': True})


@require_http_methods(['GET', 'POST'])
@require_admin
def admin_keys(request):
    if request.method == 'GET':
        keys = APIKey.objects.select_related('owner_mapping', 'owner_mapping__user').order_by('-created_at')
        now = timezone.now()
        return JsonResponse({
            'keys': [_serialize_key(k, now=now, include_owner=True) for k in keys],
        })

    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    if not data.get('name'):
        return _error('name is required')
    api_key = APIKey.objects.create(
        name=data['name'],
        description=data.get('description', ''),
        is_active=data.get('is_active', True),
        rate_limit_per_minute=data.get('rate_limit_per_minute', 60),
        rate_limit_per_hour=data.get('rate_limit_per_hour', 1000),
    )
    try:
        if 'user_id' in data:
            _set_key_owner(api_key, data.get('user_id'))
    except ValueError as exc:
        api_key.delete()
        return _error(str(exc))
    return JsonResponse({
        'success': True,
        'api_key_id': api_key.id,
        'key': api_key.key,
    })


@require_POST
@require_admin
def admin_key_update(request, key_id):
    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    try:
        api_key = APIKey.objects.get(id=key_id)
    except APIKey.DoesNotExist:
        return _error('API key not found', status=404, code='not_found')
    for field in ('name', 'description', 'is_active', 'rate_limit_per_minute', 'rate_limit_per_hour'):
        if field in data:
            setattr(api_key, field, data[field])
    api_key.save()
    try:
        if 'user_id' in data:
            _set_key_owner(api_key, data.get('user_id'))
    except ValueError as exc:
        return _error(str(exc))
    return JsonResponse({'success': True})


@require_POST
@require_admin
def admin_key_delete(request, key_id):
    try:
        api_key = APIKey.objects.get(id=key_id)
    except APIKey.DoesNotExist:
        return _error('API key not found', status=404, code='not_found')
    api_key.delete()
    return JsonResponse({'success': True})


def _serialize_admin_user(user):
    return {
        'id': user.id,
        'username': user.username,
        'role': get_user_role(user),
        'is_active': user.is_active,
        'key_ids': list(user.api_key_mappings.values_list('api_key_id', flat=True)),
    }


@require_http_methods(['GET', 'POST'])
@require_admin
def admin_users(request):
    if request.method == 'GET':
        users = User.objects.all().prefetch_related('groups', 'api_key_mappings').order_by('username')
        return JsonResponse({'users': [_serialize_admin_user(u) for u in users]})

    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    role = data.get('role', GROUP_USER)
    if not username or not password:
        return _error('username and password are required')
    if role not in (GROUP_USER, GROUP_ADMIN):
        return _error('role must be user or admin')
    if User.objects.filter(username=username).exists():
        return _error('Username already exists')
    user = User.objects.create_user(username=username, password=password)
    set_user_role(user, GROUP_ADMIN if user.is_superuser else role)
    api_key = APIKey.objects.create(
        name=f'{username} key',
        description=f'Auto-created for {username}',
    )
    UserAPIKey.objects.create(user=user, api_key=api_key)
    return JsonResponse({
        'success': True,
        'user': _serialize_admin_user(user),
        'key': api_key.key,
        'api_key_id': api_key.id,
    })


@require_POST
@require_admin
def admin_user_update(request, user_id):
    data = _json_body(request)
    if data is None:
        return _error('Invalid JSON in request body', code='invalid_json')
    try:
        user = User.objects.prefetch_related('groups').get(id=user_id)
    except User.DoesNotExist:
        return _error('User not found', status=404, code='not_found')

    if 'role' in data:
        role = data['role']
        if role not in (GROUP_USER, GROUP_ADMIN):
            return _error('role must be user or admin')
        if user.is_superuser and role != GROUP_ADMIN:
            return _error('Superusers cannot be demoted from admin')
        set_user_role(user, role)
    if 'is_active' in data:
        user.is_active = bool(data['is_active'])
        user.save(update_fields=['is_active'])
    if data.get('deactivate') is True:
        user.is_active = False
        user.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'user': _serialize_admin_user(user)})


@require_GET
@require_admin
def admin_chart_data(request):
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    hourly_data = hourly_request_series()

    model_usage = Model.objects.annotate(
        request_count=Count('requests', filter=Q(requests__created_at__gte=last_24h))
    ).filter(request_count__gt=0).values('name', 'request_count')

    model_tokens = Model.objects.annotate(
        total_tokens=Sum('requests__total_tokens', filter=Q(requests__created_at__gte=last_24h)),
        input_tokens=Sum('requests__input_tokens', filter=Q(requests__created_at__gte=last_24h)),
        output_tokens=Sum('requests__output_tokens', filter=Q(requests__created_at__gte=last_24h)),
    ).filter(total_tokens__gt=0).values('name', 'total_tokens', 'input_tokens', 'output_tokens')

    api_key_usage = APIKey.objects.annotate(
        request_count=Count('requests', filter=Q(requests__created_at__gte=last_24h)),
        total_tokens=Sum('requests__total_tokens', filter=Q(requests__created_at__gte=last_24h)),
    ).filter(request_count__gt=0).values('name', 'request_count', 'total_tokens')

    return JsonResponse({
        'hourly_requests': hourly_data,
        'model_usage': list(model_usage),
        'model_tokens': list(model_tokens),
        'api_key_usage': list(api_key_usage),
    })


@require_GET
@require_admin
def admin_request_history(request):
    queryset = LLMRequest.objects.select_related('model', 'api_key').all().order_by('-created_at')
    model_id = request.GET.get('model_id')
    api_key_id = request.GET.get('api_key_id')
    status = request.GET.get('status')
    if model_id:
        queryset = queryset.filter(model_id=model_id)
    if api_key_id:
        queryset = queryset.filter(api_key_id=api_key_id)
    if status:
        queryset = queryset.filter(status=status)
    return _paginate_requests(queryset, request)
