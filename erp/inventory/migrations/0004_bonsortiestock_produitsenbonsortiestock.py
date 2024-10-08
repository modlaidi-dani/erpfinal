# Generated by Django 4.2.5 on 2023-09-24 14:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0002_variantsprixclient'),
        ('tiers', '0002_initial'),
        ('users', '0001_initial'),
        ('clientInfo', '0002_alter_typeclient_type_desc'),
        ('inventory', '0003_bonretour_bonl_bonretour_client_bontransfert_store'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonSortieStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
                ('num_doc', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('Date_doc_Sortie', models.DateField()),
                ('num_constat', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('Date_constat', models.DateField()),
                ('note', models.TextField()),
                ('Client', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='tiers.client')),
                ('entrepot', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='Entrepots_bons_sortiesstock', to='inventory.entrepot')),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='clientInfo.store')),
                ('user', models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_sortiesstock', to='users.customuser')),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnBonSortieStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_sortie_stock', to='inventory.bonsortiestock')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bons_sorties_stock', to='produits.product')),
            ],
        ),
    ]
