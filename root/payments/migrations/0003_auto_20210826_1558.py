# Generated by Django 2.1.4 on 2021-08-26 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0002_auto_20210623_1259'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='payment_method',
            field=models.CharField(choices=[('GIFT_CARD', 'GIFT_CARD'), ('TREMENDOUS_API', 'TREMENDOUS_API')], default='TREMENDOUS_API', max_length=255),
        ),
    ]
