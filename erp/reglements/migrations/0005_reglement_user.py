# Generated by Django 4.2.5 on 2023-10-01 13:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_customuser_role'),
        ('reglements', '0004_echeancereglement_store_modereglement_store'),
    ]

    operations = [
        migrations.AddField(
            model_name='reglement',
            name='user',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='users.customuser'),
        ),
    ]
