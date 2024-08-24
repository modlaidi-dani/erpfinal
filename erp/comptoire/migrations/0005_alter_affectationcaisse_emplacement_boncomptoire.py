# Generated by Django 4.2.5 on 2023-10-12 09:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tiers', '0005_comptebancaire_compteclient_and_more'),
        ('inventory', '0014_bontransfert_automatiquement_bontransfert_valide'),
        ('clientInfo', '0009_store_product_variant'),
        ('users', '0006_alter_customuser_entrepots_responsible'),
        ('comptoire', '0004_cloture'),
    ]

    operations = [
        migrations.AlterField(
            model_name='affectationcaisse',
            name='emplacement',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.entrepot'),
        ),
        migrations.CreateModel(
            name='BonComptoire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
                ('client', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='tiers.client')),
                ('pointVente', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='comptoire.pointvente')),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='clientInfo.store')),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_comptoire', to='users.customuser')),
            ],
        ),
    ]