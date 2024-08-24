# Generated by Django 4.2.5 on 2023-10-05 11:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0013_bonreintegration_produitsenbonreintegration'),
        ('users', '0004_customuser_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='entrepots_responsible',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='inventory.entrepot'),
        ),
    ]