from django.apps import AppConfig
import threading
import time


def warmup_models_task():
    """Background task that warms up models every 3 minutes"""
    from django.core.management import call_command
    from django.db import connection
    
    while True:
        try:
            # Ensure database connection is closed before calling command
            connection.close()
            call_command('warmup_models')
        except Exception as e:
            print(f"Error in warmup task: {e}")
        
        # Sleep for 3 minutes (180 seconds)
        time.sleep(180)


class LlmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LLM'
    
    def ready(self):
        """Start background warmup task when Django is ready"""
        import sys
        import os
        
        # Skip if running migrations, tests, or shell commands
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if command in ['migrate', 'makemigrations', 'test', 'shell', 'shell_plus', 'dbshell']:
                return
        
        # Only start once (avoid starting in each worker process)
        # Check if we're in the main process (not a worker)
        if hasattr(os, 'getpid'):
            # Start warmup thread
            warmup_thread = threading.Thread(target=warmup_models_task, daemon=True)
            warmup_thread.start()
            print("Model warmup task started (runs every 3 minutes)")
