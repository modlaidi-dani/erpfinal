# Generated by Django 3.2.14 on 2024-03-25 08:26

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0023_bontransfert_received_produitsenbonretour_numseries_and_more'),
        ('tiers', '0009_region'),
        ('clientInfo', '0010_auto_20240304_1334'),
        ('users', '0010_customuser_adresse_ip'),
        ('produits', '0012_numseries'),
        ('comptoire', '0020_boncomptoire_observation'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonRectification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
                ('observation', models.CharField(blank=True, default='', max_length=4500, null=True)),
                ('totalprice', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=15, null=True)),
                ('totalremise', models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=15, null=True)),
                ('caisse', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='clientInfo.compteentreprise')),
                ('client', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mesbons_rectification', to='tiers.client')),
                ('pointVente', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='comptoire.pointvente')),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bons_rectif_store', to='clientInfo.store')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_rectification', to='users.customuser')),
            ],
        ),
        migrations.AlterField(
            model_name='bonretourcomptoir',
            name='bon_comptoir_associe',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bons_retour_compt', to='comptoire.boncomptoire'),
        ),
        migrations.AlterField(
            model_name='verssement',
            name='bon_comptoir_associe',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verssements', to='comptoire.boncomptoire'),
        ),
        migrations.CreateModel(
            name='ProduitsEnBonRectif',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('unitprice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('totalprice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_rectification', to='comptoire.bonrectification')),
                ('entrepot', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='produit_rectification', to='inventory.entrepot')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bons_rectification', to='produits.product')),
            ],
        ),
        migrations.AddField(
            model_name='bonretourcomptoir',
            name='bon_rectification_associe',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bons_retour_compt', to='comptoire.bonrectification'),
        ),
        migrations.AddField(
            model_name='verssement',
            name='bon_rectification_associe',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verssements', to='comptoire.bonrectification'),
        ),
    ]
