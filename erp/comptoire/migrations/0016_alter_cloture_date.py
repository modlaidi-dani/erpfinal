# Generated by Django 4.2.5 on 2023-11-07 09:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comptoire', '0015_alter_boncomptoire_client_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cloture',
            name='date',
            field=models.DateField(),
        ),
    ]