from django.urls import path

from . import internal_views

urlpatterns = [
    path('health', internal_views.health, name='internal_health'),
    path('public/stats', internal_views.public_stats, name='internal_public_stats'),

    path('auth/csrf', internal_views.auth_csrf, name='internal_auth_csrf'),
    path('auth/login', internal_views.auth_login, name='internal_auth_login'),
    path('auth/logout', internal_views.auth_logout, name='internal_auth_logout'),
    path('auth/me', internal_views.auth_me, name='internal_auth_me'),

    path('me/keys', internal_views.me_keys, name='internal_me_keys'),
    path('me/keys/<int:key_id>/full', internal_views.me_key_full, name='internal_me_key_full'),
    path('me/usage', internal_views.me_usage, name='internal_me_usage'),
    path('me/requests', internal_views.me_requests, name='internal_me_requests'),

    path('admin/models', internal_views.admin_models, name='internal_admin_models'),
    path('admin/models/<int:model_id>/update', internal_views.admin_model_update, name='internal_admin_model_update'),
    path('admin/models/<int:model_id>/delete', internal_views.admin_model_delete, name='internal_admin_model_delete'),

    path('admin/keys', internal_views.admin_keys, name='internal_admin_keys'),
    path('admin/keys/<int:key_id>/update', internal_views.admin_key_update, name='internal_admin_key_update'),
    path('admin/keys/<int:key_id>/delete', internal_views.admin_key_delete, name='internal_admin_key_delete'),

    path('admin/users', internal_views.admin_users, name='internal_admin_users'),
    path('admin/users/<int:user_id>/update', internal_views.admin_user_update, name='internal_admin_user_update'),

    path('admin/chart-data', internal_views.admin_chart_data, name='internal_admin_chart_data'),
    path('admin/request-history', internal_views.admin_request_history, name='internal_admin_request_history'),
]
