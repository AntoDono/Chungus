from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
import secrets


class APIKey(models.Model):
    """API Key for authenticating requests to the LLM API"""
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=255, help_text="Human-readable name for this API key")
    description = models.TextField(blank=True, help_text="Optional description")
    is_active = models.BooleanField(default=True, help_text="Whether this API key is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True, help_text="Last time this key was used")
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(
        default=60, 
        validators=[MinValueValidator(1)],
        help_text="Maximum requests per minute"
    )
    rate_limit_per_hour = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(1)],
        help_text="Maximum requests per hour"
    )
    
    # Usage statistics
    total_requests = models.BigIntegerField(default=0, help_text="Total number of requests made with this key")
    total_tokens_processed = models.BigIntegerField(default=0, help_text="Total tokens processed")
    
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"
    
    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_key():
        """Generate a secure random API key"""
        return secrets.token_urlsafe(48)
    
    def update_last_used(self):
        """Update the last_used_at timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class Model(models.Model):
    """LLM Model configuration and statistics"""
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True, help_text="Description of the model")
    model_path = models.CharField(
        max_length=500, 
        help_text="Path or identifier for the model (e.g., 'meta-llama/Llama-2-7b-chat-hf')"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this model is available")
    alwayswarm = models.BooleanField(default=False, help_text="Keep this model warm by sending periodic requests")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Provider selection
    PROVIDER_CHOICES = [
        ('vllm', 'vLLM'),
        ('ollama', 'Ollama'),
    ]
    provider = models.CharField(
        max_length=10,
        choices=PROVIDER_CHOICES,
        default='vllm',
        help_text="Provider to use for this model"
    )
    
    # Ollama configuration
    ollama_base_url = models.CharField(
        max_length=255,
        default='http://localhost:11434',
        blank=True,
        help_text="Ollama API base URL (default: http://localhost:11434)"
    )
    
    # Model configuration
    max_context_length = models.IntegerField(
        default=4096,
        validators=[MinValueValidator(1)],
        help_text="Maximum context length in tokens"
    )
    default_temperature = models.FloatField(
        default=0.7,
        help_text="Default temperature for generation"
    )
    default_max_tokens = models.IntegerField(
        default=512,
        validators=[MinValueValidator(1)],
        help_text="Default maximum tokens to generate"
    )
    
    # HuggingFace authentication
    huggingface_token = models.CharField(
        max_length=255,
        blank=True,
        help_text="HuggingFace token for accessing gated models (or set HF_TOKEN env var)"
    )
    
    # Statistics
    total_requests = models.BigIntegerField(default=0, help_text="Total requests processed")
    total_responses = models.BigIntegerField(default=0, help_text="Total successful responses")
    total_errors = models.BigIntegerField(default=0, help_text="Total errors encountered")
    total_tokens_processed = models.BigIntegerField(
        default=0, 
        help_text="Total tokens processed (input + output)"
    )
    total_input_tokens = models.BigIntegerField(default=0, help_text="Total input tokens")
    total_output_tokens = models.BigIntegerField(default=0, help_text="Total output tokens")
    
    class Meta:
        verbose_name = "Model"
        verbose_name_plural = "Models"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def increment_stats(self, input_tokens=0, output_tokens=0, success=True):
        """Increment statistics for this model"""
        self.total_requests += 1
        if success:
            self.total_responses += 1
        else:
            self.total_errors += 1
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_tokens_processed += (input_tokens + output_tokens)
        self.save(update_fields=[
            'total_requests', 'total_responses', 'total_errors',
            'total_tokens_processed', 'total_input_tokens', 'total_output_tokens'
        ])


class LLMRequest(models.Model):
    """Individual LLM API request and response"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Request details
    api_key = models.ForeignKey(
        APIKey, 
        on_delete=models.CASCADE, 
        related_name='requests',
        help_text="API key used for this request"
    )
    model = models.ForeignKey(
        Model,
        on_delete=models.CASCADE,
        related_name='requests',
        help_text="Model used for this request"
    )
    
    # Prompt and input
    prompt = models.TextField(help_text="Input prompt text")
    system_prompt = models.TextField(blank=True, help_text="Optional system prompt")
    images = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of image URLs or base64 encoded images"
    )
    
    # Request parameters
    temperature = models.FloatField(null=True, blank=True, help_text="Temperature for generation")
    max_tokens = models.IntegerField(null=True, blank=True, help_text="Maximum tokens to generate")
    top_p = models.FloatField(null=True, blank=True, help_text="Top-p sampling parameter")
    top_k = models.IntegerField(null=True, blank=True, help_text="Top-k sampling parameter")
    stream = models.BooleanField(default=False, help_text="Whether to stream the response")
    
    # Response details
    response = models.TextField(blank=True, help_text="Generated response text")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='pending',
        db_index=True
    )
    error_message = models.TextField(blank=True, help_text="Error message if request failed")
    
    # Token usage
    input_tokens = models.IntegerField(default=0, help_text="Number of input tokens")
    output_tokens = models.IntegerField(default=0, help_text="Number of output tokens")
    total_tokens = models.IntegerField(default=0, help_text="Total tokens (input + output)")
    
    # Timing
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True, help_text="When processing started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When processing completed")
    
    # Metadata
    request_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional request metadata"
    )
    response_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional response metadata"
    )
    
    class Meta:
        verbose_name = "LLM Request"
        verbose_name_plural = "LLM Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['api_key', '-created_at']),
            models.Index(fields=['model', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"Request {self.id} - {self.model.name} - {self.status}"
    
    def calculate_processing_time(self):
        """Calculate processing time in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def mark_started(self):
        """Mark the request as started"""
        self.status = 'processing'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, response_text, input_tokens=0, output_tokens=0, metadata=None):
        """Mark the request as completed with response"""
        self.status = 'completed'
        self.response = response_text
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.total_tokens = input_tokens + output_tokens
        self.completed_at = timezone.now()
        if metadata:
            self.response_metadata = metadata
        self.save(update_fields=[
            'status', 'response', 'input_tokens', 'output_tokens',
            'total_tokens', 'completed_at', 'response_metadata'
        ])
        
        # Update model statistics
        self.model.increment_stats(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=True
        )
        
        # Update API key statistics
        self.api_key.total_requests += 1
        self.api_key.total_tokens_processed += self.total_tokens
        self.api_key.update_last_used()
        self.api_key.save(update_fields=['total_requests', 'total_tokens_processed', 'last_used_at'])
    
    def mark_failed(self, error_message):
        """Mark the request as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'error_message', 'completed_at'])
        
        # Update model statistics
        self.model.increment_stats(success=False)
