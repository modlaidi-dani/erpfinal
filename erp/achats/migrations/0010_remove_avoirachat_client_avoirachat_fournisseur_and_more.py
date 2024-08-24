# Generated by Django 4.2.5 on 2023-10-15 06:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tiers", "0006_remove_client_actclient"),
        ("achats", "0009_avoirachat_store"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="avoirachat",
            name="client",
        ),
        migrations.AddField(
            model_name="avoirachat",
            name="fournisseur",
            field=models.ForeignKey(
                blank=True,
                default=None,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="avoirs_fournisseur",
                to="tiers.fournisseur",
            ),
        ),
        migrations.AddField(
            model_name="avoirachat",
            name="montant",
            field=models.CharField(default="", max_length=200),
        ),
        migrations.AlterField(
            model_name="avoirachat",
            name="motif",
            field=models.CharField(default="", max_length=200),
        ),
    ]