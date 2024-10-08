# Generated by Django 4.2.5 on 2023-09-24 10:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('produits', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonAchat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
                ('totalPrice', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnBonAchat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prixUnitaire', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('totalPrice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_achat', to='achats.bonachat')),
                ('produit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_achat', to='produits.product')),
            ],
        ),
    ]
