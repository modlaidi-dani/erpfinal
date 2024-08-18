# Generated by Django 4.2.5 on 2024-02-01 08:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0019_bonechange_bonmaintenance_bonretour_valide_and_more'),
        ('ventes', '0018_bongarantie_tps_ecoule'),
    ]

    operations = [
        migrations.CreateModel(
            name='DemandeTransfert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('etat', models.CharField(blank=True, default='', max_length=150, null=True)),
                ('BonSNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='demande_sortie_transfert', to='ventes.bonsortie')),
                ('BonTransfert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='demande_transfert', to='inventory.bontransfert')),
            ],
        ),
    ]
