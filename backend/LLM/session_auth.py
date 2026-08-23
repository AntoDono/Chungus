from functools import wraps

from django.contrib.auth.models import Group
from django.http import JsonResponse

GROUP_USER = 'user'
GROUP_ADMIN = 'admin'
VALID_ROLES = frozenset({GROUP_USER, GROUP_ADMIN})


def get_or_create_role_groups():
    user_group, _ = Group.objects.get_or_create(name=GROUP_USER)
    admin_group, _ = Group.objects.get_or_create(name=GROUP_ADMIN)
    return user_group, admin_group


def is_admin_user(user):
    return user.is_superuser or user.groups.filter(name=GROUP_ADMIN).exists()


def get_user_role(user):
    return GROUP_ADMIN if is_admin_user(user) else GROUP_USER


def assign_default_groups(user, created=False):
    """On user create: assign user group; superusers also get admin group."""
    user_group, admin_group = get_or_create_role_groups()
    if created:
        user.groups.add(user_group)
    if user.is_superuser:
        user.groups.add(admin_group)


def set_user_role(user, role):
    if role not in VALID_ROLES:
        raise ValueError('role must be user or admin')
    user_group, admin_group = get_or_create_role_groups()
    user.groups.add(user_group)
    if role == GROUP_ADMIN or user.is_superuser:
        user.groups.add(admin_group)
    else:
        user.groups.remove(admin_group)


def user_payload(user):
    return {
        'id': user.id,
        'username': user.username,
        'role': get_user_role(user),
    }


def require_session(view_func):
    """Require an authenticated Django session. Returns JSON 401 instead of a login redirect."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': {
                    'message': 'Authentication required',
                    'type': 'authentication_error',
                    'code': 'authentication_required',
                }
            }, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def require_admin(view_func):
    """Require admin group membership or superuser (superuser always passes for /admin fallback)."""

    @wraps(view_func)
    @require_session
    def wrapper(request, *args, **kwargs):
        if not is_admin_user(request.user):
            return JsonResponse({
                'error': {
                    'message': 'Admin role required',
                    'type': 'authorization_error',
                    'code': 'forbidden',
                }
            }, status=403)
        return view_func(request, *args, **kwargs)

    return wrapper
