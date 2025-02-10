# Generated by Django 4.0.4 on 2023-04-19 21:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0005_alter_paymentlog_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='payment_method',
            field=models.CharField(choices=[('TREMENDOUS_API', 'TREMENDOUS_API'), ('GIFT_CARD', 'GIFT_CARD')], default='TREMENDOUS_API', max_length=255),
        ),
    ]
