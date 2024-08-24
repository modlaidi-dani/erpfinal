# Generated by Django 4.2.5 on 2024-01-11 13:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clientInfo', '0009_store_product_variant'),
        ('reglements', '0011_montantcollected_cloturereglements'),
    ]

    operations = [
        migrations.AddField(
            model_name='cloturereglements',
            name='caisse',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='clotures_reg', to='clientInfo.compteentreprise'),
        ),
        migrations.AddField(
            model_name='montantcollected',
            name='caisse',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='montantcollected_reg', to='clientInfo.compteentreprise'),
        ),
    ]