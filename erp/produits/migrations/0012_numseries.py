# Generated by Django 4.2.5 on 2024-03-09 22:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("produits", "0011_alter_product_reference"),
    ]

    operations = [
        migrations.CreateModel(
            name="NumSeries",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("numseries", models.CharField(max_length=250)),
                (
                    "produit",
                    models.ForeignKey(
                        blank=True,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="myserialnumbers",
                        to="produits.product",
                    ),
                ),
            ],
        ),
    ]