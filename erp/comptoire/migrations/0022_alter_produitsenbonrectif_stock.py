# Generated by Django 3.2.14 on 2024-03-31 09:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0012_numseries'),
        ('comptoire', '0021_auto_20240325_0926'),
    ]

    operations = [
        migrations.AlterField(
            model_name='produitsenbonrectif',
            name='stock',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bons_rectif', to='produits.product'),
        ),
    ]
