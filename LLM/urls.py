from django.urls import path
from . import views

app_name = 'llm'

urlpatterns = [
    path('v1/chat/completions', views.chat_completions, name='chat_completions'),
    path('v1/embeddings', views.embeddings, name='embeddings'),
    path('v1/models', views.list_models, name='list_models'),
]

