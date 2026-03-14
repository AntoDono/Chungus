from django.urls import path
from . import views, api_views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('api-docs/', views.api_docs, name='api_docs'),
    # API endpoints
    path('api/models/', api_views.get_models, name='api_get_models'),
    path('api/models/create/', api_views.create_model, name='api_create_model'),
    path('api/models/<int:model_id>/update/', api_views.update_model, name='api_update_model'),
    path('api/models/<int:model_id>/delete/', api_views.delete_model, name='api_delete_model'),
    path('api/keys/', api_views.get_api_keys, name='api_get_api_keys'),
    path('api/keys/create/', api_views.create_api_key, name='api_create_api_key'),
    path('api/keys/<int:api_key_id>/update/', api_views.update_api_key, name='api_update_api_key'),
    path('api/keys/<int:api_key_id>/delete/', api_views.delete_api_key, name='api_delete_api_key'),
    path('api/keys/<int:api_key_id>/full/', api_views.get_api_key_full, name='api_get_api_key_full'),
    path('api/chart-data/', api_views.get_chart_data, name='api_get_chart_data'),
    path('api/request-history/', api_views.get_request_history, name='api_get_request_history'),
]

