# Generated by Django 4.2.5 on 2024-01-01 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ventes", "0016_bonsortie_modifiable"),
    ]

    operations = [
        migrations.AddField(
            model_name="bonsortie",
            name="fraisLivraisonexterne",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]
