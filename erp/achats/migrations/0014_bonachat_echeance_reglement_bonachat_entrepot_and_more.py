# Generated by Django 4.2.5 on 2023-10-31 15:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reglements', '0006_reglementfournisseur'),
        ('clientInfo', '0009_store_product_variant'),
        ('inventory', '0016_alter_bonentry_user_alter_bonreforme_user_and_more'),
        ('achats', '0013_alter_bonachat_user_alter_boncommandeachat_user_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonachat',
            name='echeance_reglement',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bonachatt_reglements_echeance', to='reglements.echeancereglement'),
        ),
        migrations.AddField(
            model_name='bonachat',
            name='entrepot',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entrepot_bonachat', to='inventory.entrepot'),
        ),
        migrations.AddField(
            model_name='bonachat',
            name='mode_reglement',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bonachat_reglements_type', to='reglements.modereglement'),
        ),
        migrations.AddField(
            model_name='bonachat',
            name='monnaie',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='monnaie_bonachat', to='clientInfo.valeurdevise'),
        ),
    ]