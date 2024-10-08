# Generated by Django 4.2.5 on 2023-09-24 10:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Journal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, default='', max_length=2500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='PlanComptableClass',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='store',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('location', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='typeClient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_desc', models.CharField(choices=[('clientfinal', 'clientfinal'), ('revendeur', 'revendeur'), ('revendeur_bronze', 'revendeur_bronze'), ('revendeur_silver', 'revendeur_silver'), ('revendeur_gold', 'revendeur_gold'), ('revendeur_diamond', 'revendeur_diamond')], default='clientfinal', max_length=25)),
                ('dateCreation', models.DateField(blank=True, default='2023-08-22', null=True)),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entreprise_typeClient', to='clientInfo.store')),
            ],
        ),
        migrations.CreateModel(
            name='Taxes',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('libelle', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('taux', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('type_taxe', models.CharField(choices=[('TVA', 'TVA'), ('DOUAN', 'DOUAN')], max_length=30)),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entreprise_taxes', to='clientInfo.store')),
            ],
        ),
        migrations.CreateModel(
            name='PlanComptableAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=100)),
                ('comptable_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clientInfo.plancomptableclass')),
            ],
        ),
        migrations.CreateModel(
            name='Devise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('designation', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('symbole', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('actif', models.BooleanField(default=True)),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entreprise_devise', to='clientInfo.store')),
            ],
        ),
        migrations.CreateModel(
            name='CompteEntreprise',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nature', models.CharField(choices=[('Caisse', 'Caisse'), ('Banque', 'Banque'), ('CCP', 'CCP'), ('Autres', 'Autres')], max_length=30)),
                ('label', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('numCompte', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('journal', models.CharField(blank=True, default='', max_length=2500, null=True)),
                ('monnaie', models.CharField(choices=[('Caisse', 'Caisse'), ('Banque', 'Banque'), ('CCP', 'CCP'), ('Autres', 'Autres')], max_length=30)),
                ('compteComptable', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comptable_compteEntreprise', to='clientInfo.plancomptableaccount')),
                ('store', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='entreprise_comptes', to='clientInfo.store')),
            ],
        ),
    ]
