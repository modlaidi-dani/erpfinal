# Generated by Django 4.2.5 on 2024-07-17 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventes', '0026_remove_bonsortie_etat_reglement_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonsortie',
            name='totalPrice',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15),
        ),
    ]
