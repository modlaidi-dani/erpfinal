# Generated by Django 3.2.14 on 2024-03-31 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestionRH', '0008_requetesalarie'),
    ]

    operations = [
        migrations.CreateModel(
            name='BoiteArchive',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('date_facturation_fournisseur', models.DateTimeField(auto_now_add=True)),
                ('date_facturation_transitaire', models.DateTimeField(auto_now_add=True)),
                ('montant', models.DecimalField(decimal_places=2, default=0, max_digits=35)),
                ('typedocument', models.CharField(default='', max_length=255)),
                ('label', models.CharField(default='', max_length=255)),
                ('document', models.FileField(upload_to='document')),
            ],
        ),
    ]