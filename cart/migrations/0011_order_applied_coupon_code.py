# Generated by Django 5.2 on 2025-07-14 07:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0010_alter_wallet_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='applied_coupon_code',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
