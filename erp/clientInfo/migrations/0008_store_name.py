# Generated by Django 4.2.5 on 2023-09-28 10:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientInfo', '0007_remove_store_name_store_codepostal_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='store',
            name='name',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
    ]
