# Generated by Django 5.0.1 on 2025-05-01 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_app', '0005_alter_transaction_currency_alter_transaction_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transaction',
            name='status',
            field=models.CharField(default='pending', max_length=20),
        ),
    ]
