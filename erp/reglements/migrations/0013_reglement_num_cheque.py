# Generated by Django 3.2.23 on 2024-02-11 08:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reglements', '0012_cloturereglements_caisse_montantcollected_caisse'),
    ]

    operations = [
        migrations.AddField(
            model_name='reglement',
            name='num_cheque',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
    ]