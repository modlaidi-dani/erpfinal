# Generated by Django 4.2.5 on 2023-09-26 15:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0008_inventorycustompermission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bonsortiestock',
            name='note',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]
