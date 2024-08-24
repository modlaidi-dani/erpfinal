# Generated by Django 4.2.5 on 2024-08-07 15:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ventes', '0027_bonsortie_totalprice'),
    ]

    operations = [
        migrations.AddField(
            model_name='bonsortie',
            name='confirmed',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='ConfirmationBl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dateConfirmation', models.DateTimeField()),
                ('dateLivraisonPrevu', models.DateField()),
                ('fichier_confirmation', models.FileField(upload_to='media/document')),
                ('BonNo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='confrimation_bon', to='ventes.bonsortie')),
            ],
        ),
    ]