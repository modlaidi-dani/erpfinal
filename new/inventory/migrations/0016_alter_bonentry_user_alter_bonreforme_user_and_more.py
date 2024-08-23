# Generated by Django 4.2.5 on 2023-10-23 10:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_rename_logentry_mylogentry'),
        ('inventory', '0015_bonreforme_bonretour_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bonentry',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_entry', to='users.customuser'),
        ),
        migrations.AlterField(
            model_name='bonreforme',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_reforme', to='users.customuser'),
        ),
        migrations.AlterField(
            model_name='bonreintegration',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_reintegration', to='users.customuser'),
        ),
        migrations.AlterField(
            model_name='bonretour',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_retour', to='users.customuser'),
        ),
        migrations.AlterField(
            model_name='bonsortiedestock',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_sortiesstock', to='users.customuser'),
        ),
        migrations.AlterField(
            model_name='bontransfert',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_transfert', to='users.customuser'),
        ),
    ]
