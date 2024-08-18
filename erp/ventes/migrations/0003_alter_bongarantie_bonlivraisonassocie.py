# Generated by Django 4.2.5 on 2023-09-25 21:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("ventes", "0002_ventescustompermission"),
    ]

    operations = [
        migrations.AlterField(
            model_name="bongarantie",
            name="bonLivraisonAssocie",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="bon_garantie",
                to="ventes.bonsortie",
            ),
        ),
    ]
