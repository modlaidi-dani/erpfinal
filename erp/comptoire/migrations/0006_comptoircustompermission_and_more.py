# Generated by Django 4.2.5 on 2023-10-12 13:37

import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('users', '0006_alter_customuser_entrepots_responsible'),
        ('comptoire', '0005_alter_affectationcaisse_emplacement_boncomptoire'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComptoirCustomPermission',
            fields=[
                ('permission_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='auth.permission')),
            ],
            options={
                'verbose_name': 'Custom Permission',
                'verbose_name_plural': 'Custom Permissions',
            },
            bases=('auth.permission',),
            managers=[
                ('objects', django.contrib.auth.models.PermissionManager()),
            ],
        ),
        migrations.AlterField(
            model_name='affectationcaisse',
            name='utilisateur',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mon_affectation', to='users.customuser'),
        ),
    ]
