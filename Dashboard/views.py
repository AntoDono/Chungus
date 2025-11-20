from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q
from LLM.models import Model, APIKey, LLMRequest


def superuser_required(user):
    """Check if user is a superuser"""
    return user.is_authenticated and user.is_superuser


def index(request):
    """
    Index/home page with military design
    """
    return render(request, 'Dashboard/index.html')


def api_docs(request):
    """
    API Documentation page
    """
    return render(request, 'Dashboard/api_docs.html')


@login_required(login_url='/admin/login/')
@user_passes_test(superuser_required, login_url='/admin/login/')
def dashboard(request):
    """
    Superuser-only dashboard page with LLM stats
    """
    # Get time ranges
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    
    # Overall stats
    total_models = Model.objects.count()
    active_models = Model.objects.filter(is_active=True).count()
    total_api_keys = APIKey.objects.count()
    active_api_keys = APIKey.objects.filter(is_active=True).count()
    
    # Request stats
    total_requests = LLMRequest.objects.count()
    requests_24h = LLMRequest.objects.filter(created_at__gte=last_24h).count()
    requests_7d = LLMRequest.objects.filter(created_at__gte=last_7d).count()
    
    # Token stats
    token_stats = LLMRequest.objects.aggregate(
        total_input=Sum('input_tokens'),
        total_output=Sum('output_tokens'),
        total_tokens=Sum('total_tokens')
    )
    
    # Model stats
    model_stats = Model.objects.annotate(
        request_count=Count('requests'),
        total_tokens=Sum('requests__total_tokens')
    ).order_by('-request_count')[:10]
    
    # API key stats
    api_key_stats = APIKey.objects.annotate(
        request_count=Count('requests')
    ).order_by('-request_count')[:10]
    
    # Recent requests for chart data (simplified - will be handled by API)
    recent_requests_24h = []
    
    # Status breakdown
    status_breakdown = LLMRequest.objects.values('status').annotate(
        count=Count('id')
    )
    
    context = {
        'user': request.user,
        'is_superuser': request.user.is_superuser,
        'total_models': total_models,
        'active_models': active_models,
        'total_api_keys': total_api_keys,
        'active_api_keys': active_api_keys,
        'total_requests': total_requests,
        'requests_24h': requests_24h,
        'requests_7d': requests_7d,
        'token_stats': token_stats,
        'model_stats': list(model_stats.values('name', 'request_count', 'total_tokens', 'is_active')),
        'api_key_stats': list(api_key_stats.values('name', 'request_count', 'total_requests', 'is_active')),
        'recent_requests_24h': list(recent_requests_24h),
        'status_breakdown': list(status_breakdown),
    }
    return render(request, 'Dashboard/dashboard.html', context)

