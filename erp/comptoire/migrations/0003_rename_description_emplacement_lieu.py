# Generated by Django 4.2.5 on 2023-10-10 14:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comptoire', '0002_affectationcaisse_store_emplacement_store_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='emplacement',
            old_name='description',
            new_name='lieu',
        ),
    ]
