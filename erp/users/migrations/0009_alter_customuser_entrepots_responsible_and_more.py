# Generated by Django 4.2.5 on 2023-12-11 08:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0016_alter_bonentry_user_alter_bonreforme_user_and_more'),
        ('clientInfo', '0009_store_product_variant'),
        ('users', '0008_rename_logentry_mylogentry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='entrepots_responsible',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='responsables', to='inventory.entrepot'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='group',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='group_users', to='users.customgroup'),
        ),
        migrations.CreateModel(
            name='Equipe',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(blank=True, default='', max_length=250, null=True)),
                ('date_created', models.DateTimeField()),
                ('store', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mes_equipes', to='clientInfo.store')),
            ],
        ),
        migrations.AddField(
            model_name='customuser',
            name='equipe_affiliated',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mes_membres', to='users.equipe'),
        ),
    ]
