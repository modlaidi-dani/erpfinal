# Generated by Django 4.2.5 on 2023-10-01 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_remove_customuser_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='role',
            field=models.CharField(blank=True, default='', max_length=100, null=True),
        ),
    ]
