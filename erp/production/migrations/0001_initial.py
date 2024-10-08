# Generated by Django 4.2.5 on 2024-01-23 08:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('inventory', '0018_stock_quantity_initial'),
        ('clientInfo', '0009_store_product_variant'),
        ('produits', '0010_product_prix_livraison'),
    ]

    operations = [
        migrations.CreateModel(
            name='ordreFabrication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codeOrdre', models.CharField(max_length=255)),
                ('entrepot_destocker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ordre_fabrication_destock', to='inventory.entrepot')),
                ('entrepot_stocker', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ordre_fabrication_stock', to='inventory.entrepot')),
                ('pc_created', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordre_creation', to='produits.product')),
                ('store', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='clientInfo.store')),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnOrdreFabrication',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_ordre_fabrication', to='production.ordrefabrication')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ordres_fabriquation', to='produits.product')),
            ],
        ),
    ]
