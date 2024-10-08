# Generated by Django 4.2.5 on 2023-09-24 10:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('produits', '0001_initial'),
        ('clientInfo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='BonRetour',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
                ('totalPrice', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='BonTransfert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='Entrepot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('adresse', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('ville', models.CharField(max_length=100)),
                ('codePostal', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('phone', models.CharField(blank=True, default='', max_length=100, null=True)),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='store_entrepot', to='clientInfo.store')),
            ],
        ),
        migrations.CreateModel(
            name='Stock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=0)),
                ('entrepot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='inventories', to='inventory.entrepot')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mon_stock', to='produits.product')),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnBonTransfert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_transfert', to='inventory.bontransfert')),
                ('stock_arr', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bons_transfert_recu', to='inventory.stock')),
                ('stock_dep', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bons_transfert_arrive', to='inventory.stock')),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnBonRetour',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('totalprice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('unitprice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_retour', to='inventory.bonretour')),
                ('produit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_retour', to='produits.product')),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnBonEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_entry', to='inventory.bonentry')),
                ('stock', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bons_entry', to='produits.product')),
            ],
        ),
        migrations.AddField(
            model_name='bontransfert',
            name='entrepot_arrive',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='bontransfert_rec', to='inventory.entrepot'),
        ),
        migrations.AddField(
            model_name='bontransfert',
            name='entrepot_depart',
            field=models.ForeignKey(blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='bontransfert_env', to='inventory.entrepot'),
        ),
    ]
