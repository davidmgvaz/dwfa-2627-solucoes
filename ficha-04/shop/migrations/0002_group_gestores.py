"""Grupo `gestores` em todos os ambientes (CI incluído) · the role group everywhere, CI included."""

from django.db import migrations

GROUP = "gestores"


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name=GROUP)


def backwards(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=GROUP).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0001_initial_domain"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]
