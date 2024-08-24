# Generated by Django 3.2.14 on 2024-03-31 09:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clientInfo', '0010_auto_20240304_1334'),
        ('users', '0010_customuser_adresse_ip'),
        ('inventory', '0023_bontransfert_received_produitsenbonretour_numseries_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='BonRetourAncien',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('idBon', models.CharField(max_length=200, unique=True, verbose_name='id Bon')),
                ('dateBon', models.DateField()),
                ('totalPrice', models.IntegerField(default=0)),
                ('bonL', models.CharField(max_length=100)),
                ('client', models.CharField(max_length=100)),
                ('valide', models.BooleanField(blank=True, default=False, null=True)),
                ('entrepot', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entrepot_retourancien', to='inventory.entrepot')),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='store_bons_retour_ancien', to='clientInfo.store')),
                ('user', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_bons_retour_ancien', to='users.customuser')),
            ],
        ),
        migrations.CreateModel(
            name='ProduitsEnBonRetourAncien',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('referenceproduit', models.CharField(max_length=100)),
                ('nomproduit', models.CharField(max_length=100)),
                ('totalprice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('unitprice', models.DecimalField(decimal_places=2, max_digits=15)),
                ('reintegrated', models.BooleanField(default=False)),
                ('warranty', models.BooleanField(default=False)),
                ('numseries', models.CharField(blank=True, default='', max_length=200, null=True)),
                ('quantity', models.IntegerField(default=1)),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='produits_en_bon_retourancien', to='inventory.bonretourancien')),
            ],
        ),
    ]