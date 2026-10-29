from django.db import migrations

def seed_rbac_data(apps, schema_editor):
    from apps.core.seeder import ensure_rbac_seeded
    ensure_rbac_seeded(force_reset=False)

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_appmodule_rolepermission_userpermissionoverride'),
    ]

    operations = [
        migrations.RunPython(seed_rbac_data, reverse_code=migrations.RunPython.noop),
    ]
