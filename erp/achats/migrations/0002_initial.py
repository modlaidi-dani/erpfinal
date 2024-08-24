# Generated by Django 4.2.5 on 2023-09-24 10:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tiers', '0001_initial'),
        ('clientInfo', '0001_initial'),
        ('achats', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonachat',
            name='fournisseur',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='client_bons_achat', to='tiers.fournisseur'),
        ),
        migrations.AddField(
            model_name='bonachat',
            name='store',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='store_bons_achat', to='clientInfo.store'),
        ),
    ]
