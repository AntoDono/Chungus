from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_user_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('LLM', 'UserProfile')
    for user in User.objects.all():
        role = 'admin' if user.is_superuser else 'user'
        UserProfile.objects.get_or_create(user=user, defaults={'role': role})


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('LLM', '0011_model_is_default'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('user', 'User'), ('admin', 'Admin')],
                    default='user',
                    max_length=10,
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
            },
        ),
        migrations.CreateModel(
            name='UserAPIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('api_key', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='owner_mapping',
                    to='LLM.apikey',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='api_key_mappings',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'User API Key Mapping',
                'verbose_name_plural': 'User API Key Mappings',
            },
        ),
        migrations.RunPython(backfill_user_profiles, noop_reverse),
    ]
