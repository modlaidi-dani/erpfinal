# Generated by Django 4.2.5 on 2023-10-10 11:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0014_bontransfert_automatiquement_bontransfert_valide'),
        ('users', '0005_customuser_entrepots_responsible'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='entrepots_responsible',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='responsables', to='inventory.entrepot'),
        ),
    ]
