# Generated by Django 4.2.5 on 2023-09-26 08:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_inventorycustompermission'),
        ('produits', '0004_produitscustompermission'),
    ]

    operations = [
        migrations.AddField(
            model_name='verificationarchive',
            name='entrepot',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.entrepot'),
        ),
    ]
