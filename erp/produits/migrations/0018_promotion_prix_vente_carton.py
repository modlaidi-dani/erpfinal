# Generated by Django 4.2.5 on 2024-05-26 09:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("produits", "0017_product_quantitypercarton_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="promotion",
            name="prix_vente_carton",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]