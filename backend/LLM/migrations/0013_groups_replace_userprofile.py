from django.db import migrations


def migrate_roles_to_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('LLM', 'UserProfile')

    user_group, _ = Group.objects.get_or_create(name='user')
    admin_group, _ = Group.objects.get_or_create(name='admin')

    profile_user_ids = set()
    for profile in UserProfile.objects.select_related('user').all():
        user = profile.user
        profile_user_ids.add(user.id)
        user.groups.add(user_group)
        if profile.role == 'admin' or user.is_superuser:
            user.groups.add(admin_group)

    for user in User.objects.exclude(id__in=profile_user_ids):
        user.groups.add(user_group)
        if user.is_superuser:
            user.groups.add(admin_group)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('LLM', '0012_role'),
    ]

    operations = [
        migrations.RunPython(migrate_roles_to_groups, noop_reverse),
        migrations.DeleteModel(name='UserProfile'),
    ]
