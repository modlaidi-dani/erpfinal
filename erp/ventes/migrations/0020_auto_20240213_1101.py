# Generated by Django 3.2.23 on 2024-02-13 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ventes', '0019_demandetransfert'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonsortie',
            name='name_pc',
            field=models.CharField(blank=True, default='', max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='bonsortie',
            name='reference_pc',
            field=models.CharField(blank=True, default='', max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='bonsortie',
            name='idBon',
            field=models.CharField(max_length=200, verbose_name='id Bon'),
        ),
    ]
