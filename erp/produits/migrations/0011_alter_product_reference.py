# Generated by Django 3.2.23 on 2024-02-11 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0010_product_prix_livraison'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='reference',
            field=models.CharField(help_text='Référence interne pour ce produit', max_length=120, verbose_name='Référence du produit'),
        ),
    ]
