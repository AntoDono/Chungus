from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('LLM', '0010_thinking_mode_levels'),
    ]

    operations = [
        migrations.AddField(
            model_name='model',
            name='is_default',
            field=models.BooleanField(
                default=False,
                help_text='Use as fallback when the requested model is missing or inactive',
            ),
        ),
    ]
