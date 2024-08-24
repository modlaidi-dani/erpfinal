# Generated by Django 4.2.5 on 2024-05-28 14:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('produits', '0019_codeea'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoriqueAchatProduit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qty_qctuelle', models.IntegerField(default=0)),
                ('prix_achat_actuelle', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('qty_achete', models.IntegerField(default=0)),
                ('prix_achat', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('prix_achat_calcule', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('dateAchat', models.DateField()),
                ('produit', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='monHIstoriqueAchat', to='produits.product')),
            ],
        ),
    ]