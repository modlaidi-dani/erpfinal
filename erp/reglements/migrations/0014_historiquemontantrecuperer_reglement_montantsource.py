# Generated by Django 4.2.5 on 2024-07-01 00:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tiers', '0012_prospectionclient_tentatives'),
        ('reglements', '0013_reglement_num_cheque'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoriqueMontantRecuperer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('montant', models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True)),
                ('date', models.DateField()),
                ('client', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='montant_envoye', to='tiers.client')),
            ],
        ),
        migrations.AddField(
            model_name='reglement',
            name='montantSource',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='rep_reglements', to='reglements.historiquemontantrecuperer'),
        ),
    ]