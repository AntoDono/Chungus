from django.contrib import admin
from .models import APIKey, Model, LLMRequest


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'key_preview', 'is_active', 'total_requests', 'total_tokens_processed', 'last_used_at', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_used_at']
    search_fields = ['name', 'key', 'description']
    readonly_fields = ['key', 'created_at', 'updated_at', 'total_requests', 'total_tokens_processed']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'key', 'is_active')
        }),
        ('Rate Limiting', {
            'fields': ('rate_limit_per_minute', 'rate_limit_per_hour')
        }),
        ('Statistics', {
            'fields': ('total_requests', 'total_tokens_processed', 'last_used_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def key_preview(self, obj):
        """Show first 8 characters of the key"""
        return f"{obj.key[:8]}..." if obj.key else "-"
    key_preview.short_description = "Key Preview"


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider', 'model_path', 'is_active', 'total_requests', 'total_responses', 'total_errors', 'total_tokens_processed', 'created_at']
    list_filter = ['is_active', 'provider', 'created_at']
    search_fields = ['name', 'model_path', 'description']
    readonly_fields = ['created_at', 'updated_at', 'total_requests', 'total_responses', 'total_errors', 'total_tokens_processed', 'total_input_tokens', 'total_output_tokens']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'model_path', 'provider', 'is_active')
        }),
        ('Provider Configuration', {
            'fields': ('ollama_base_url', 'huggingface_token'),
            'description': 'Configure provider-specific settings'
        }),
        ('Model Configuration', {
            'fields': ('max_context_length', 'default_temperature', 'default_max_tokens')
        }),
        ('Statistics', {
            'fields': (
                'total_requests', 'total_responses', 'total_errors',
                'total_tokens_processed', 'total_input_tokens', 'total_output_tokens'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(LLMRequest)
class LLMRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'api_key', 'model', 'status', 'input_tokens', 'output_tokens', 'total_tokens', 'created_at', 'completed_at']
    list_filter = ['status', 'model', 'api_key', 'created_at', 'stream']
    search_fields = ['prompt', 'response', 'error_message', 'api_key__name', 'model__name']
    readonly_fields = ['created_at', 'updated_at', 'total_tokens', 'processing_time']
    fieldsets = (
        ('Request Information', {
            'fields': ('api_key', 'model', 'status')
        }),
        ('Input', {
            'fields': ('prompt', 'system_prompt', 'images')
        }),
        ('Parameters', {
            'fields': ('temperature', 'max_tokens', 'top_p', 'top_k', 'stream')
        }),
        ('Response', {
            'fields': ('response', 'error_message', 'response_metadata')
        }),
        ('Token Usage', {
            'fields': ('input_tokens', 'output_tokens', 'total_tokens')
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'updated_at', 'processing_time')
        }),
        ('Metadata', {
            'fields': ('request_metadata',)
        }),
    )
    
    def processing_time(self, obj):
        """Display processing time"""
        time = obj.calculate_processing_time()
        return f"{time:.2f}s" if time else "-"
    processing_time.short_description = "Processing Time"
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('api_key', 'model')
