# Generated by Django 4.0.4 on 2024-12-20 21:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0024_alter_paymentlog_payment_method_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('OTHER', 'OTHER'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='reviewquestion',
            name='type',
            field=models.CharField(blank=True, choices=[('TEXTFIELD', 'TEXTFIELD'), ('DROPDOWN', 'DROPDOWN'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE'), ('YES_NO', 'YES_NO')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('OTHER', 'OTHER'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE')], max_length=255, null=True),
        ),
    ]
