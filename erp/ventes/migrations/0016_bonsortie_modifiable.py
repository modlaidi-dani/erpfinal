# Generated by Django 4.1.7 on 2023-12-20 08:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventes', '0015_bonsortie_agencelivraison_bonsortie_fraislivraison'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonsortie',
            name='modifiable',
            field=models.BooleanField(default=False),
        ),
    ]
