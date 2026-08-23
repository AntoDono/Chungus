from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .session_auth import assign_default_groups


@receiver(post_save, sender=User)
def assign_user_groups(sender, instance, created, **kwargs):
    assign_default_groups(instance, created=created)
