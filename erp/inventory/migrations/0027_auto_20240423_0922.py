# Generated by Django 3.2.14 on 2024-04-23 08:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0026_auto_20240421_0952'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonmaintenance',
            name='garantie',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.AddField(
            model_name='bonmaintenance',
            name='reponse',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]