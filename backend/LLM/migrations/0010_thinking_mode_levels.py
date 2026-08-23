from django.db import migrations, models


def migrate_model_thinking_mode(apps, schema_editor):
    Model = apps.get_model('LLM', 'Model')
    Model.objects.filter(thinking_mode='auto').update(thinking_mode='default')


def migrate_thinking_values(apps, schema_editor):
    LLMRequest = apps.get_model('LLM', 'LLMRequest')
    for request in LLMRequest.objects.exclude(thinking__isnull=True):
        if request.thinking is True:
            request.thinking_value = 'true'
        elif request.thinking is False:
            request.thinking_value = 'false'
        request.save(update_fields=['thinking_value'])


class Migration(migrations.Migration):

    dependencies = [
        ('LLM', '0009_llmrequest_thinking_model_thinking_mode'),
    ]

    operations = [
        migrations.RunPython(migrate_model_thinking_mode, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='model',
            name='thinking_mode',
            field=models.CharField(
                choices=[
                    ('default', 'Default (let model decide)'),
                    ('low', 'Low'),
                    ('medium', 'Medium'),
                    ('high', 'High'),
                    ('enabled', 'Enabled'),
                    ('disabled', 'Disabled'),
                    ('auto', 'Auto (alias for default)'),
                ],
                default='default',
                help_text='Default thinking mode for this model (Ollama only)',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='llmrequest',
            name='thinking_value',
            field=models.CharField(
                blank=True,
                help_text='Thinking mode for this request (null = use model default)',
                max_length=10,
                null=True,
            ),
        ),
        migrations.RunPython(migrate_thinking_values, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='llmrequest',
            name='thinking',
        ),
        migrations.RenameField(
            model_name='llmrequest',
            old_name='thinking_value',
            new_name='thinking',
        ),
    ]
