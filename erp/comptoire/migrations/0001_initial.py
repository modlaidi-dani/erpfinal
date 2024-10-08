# Generated by Django 4.2.5 on 2023-10-10 11:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('reglements', '0006_reglementfournisseur'),
        ('users', '0005_customuser_entrepots_responsible'),
        ('clientInfo', '0009_store_product_variant'),
        ('inventory', '0014_bontransfert_automatiquement_bontransfert_valide'),
    ]

    operations = [
        migrations.CreateModel(
            name='Emplacement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Label', models.TextField(blank=True, default='', null=True)),
                ('description', models.TextField(blank=True, default='', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='pointVente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=200)),
                ('type_reglement', models.CharField(max_length=200)),
                ('adresse', models.TextField(blank=True, default='', null=True)),
                ('Téléphone', models.TextField(blank=True, default='', null=True)),
                ('entrepot', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_points_ventes', to='inventory.entrepot')),
                ('mode_payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pointVentes', to='reglements.modereglement')),
            ],
        ),
        migrations.CreateModel(
            name='AffectationCaisse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('CompteTres', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='clientInfo.compteentreprise')),
                ('emplacement', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='comptoire.emplacement')),
                ('utilisateur', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.customuser')),
            ],
        ),
    ]
