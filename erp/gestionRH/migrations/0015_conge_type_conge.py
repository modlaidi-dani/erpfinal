# Generated by Django 4.2.5 on 2024-07-09 12:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionRH', '0014_reglementcompte'),
    ]

    operations = [
        migrations.AddField(
            model_name='conge',
            name='type_conge',
            field=models.TextField(default=''),
        ),
    ]