# Generated by Django 4.2.5 on 2023-09-27 09:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientInfo', '0004_compteentreprise_agence_compteentreprise_banque'),
    ]

    operations = [
        migrations.AlterField(
            model_name='compteentreprise',
            name='monnaie',
            field=models.CharField(blank=True, default='', max_length=2500, null=True),
        ),
    ]