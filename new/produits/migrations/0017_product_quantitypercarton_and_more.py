# Generated by Django 4.2.5 on 2024-05-26 09:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("produits", "0016_promotion"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="QuantityPerCarton",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="variantsprixclient",
            name="prix_vente_carton",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]
