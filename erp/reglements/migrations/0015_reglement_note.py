# Generated by Django 4.2.5 on 2024-07-04 08:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reglements', '0014_historiquemontantrecuperer_reglement_montantsource'),
    ]

    operations = [
        migrations.AddField(
            model_name='reglement',
            name='note',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]