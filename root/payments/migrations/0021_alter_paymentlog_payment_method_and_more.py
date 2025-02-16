# Generated by Django 4.0.4 on 2024-12-14 00:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0020_alter_paymentlog_reason_alter_reviewquestion_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='payment_method',
            field=models.CharField(choices=[('WINGSPAN_API', 'WINGSPAN_API'), ('GIFT_CARD', 'GIFT_CARD')], default='TREMENDOUS_API', max_length=255),
        ),
        migrations.AlterField(
            model_name='paymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('OTHER', 'OTHER'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='reviewquestion',
            name='type',
            field=models.CharField(blank=True, choices=[('DROPDOWN', 'DROPDOWN'), ('TEXTFIELD', 'TEXTFIELD'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE'), ('YES_NO', 'YES_NO')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='payment_method',
            field=models.CharField(choices=[('WINGSPAN_API', 'WINGSPAN_API'), ('GIFT_CARD', 'GIFT_CARD')], default='WINGSPAN_API', max_length=255),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('OTHER', 'OTHER'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE')], max_length=255, null=True),
        ),
    ]
