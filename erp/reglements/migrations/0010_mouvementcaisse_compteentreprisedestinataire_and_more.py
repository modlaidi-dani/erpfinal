# Generated by Django 4.2.5 on 2024-01-10 08:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clientInfo', '0009_store_product_variant'),
        ('reglements', '0009_typedepense_depense'),
    ]

    operations = [
        migrations.AddField(
            model_name='mouvementcaisse',
            name='CompteEntrepriseDestinataire',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mouvements_recu', to='clientInfo.compteentreprise'),
        ),
        migrations.AlterField(
            model_name='mouvementcaisse',
            name='CompteEntreprise',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mouvements_sortie', to='clientInfo.compteentreprise'),
        ),
    ]
