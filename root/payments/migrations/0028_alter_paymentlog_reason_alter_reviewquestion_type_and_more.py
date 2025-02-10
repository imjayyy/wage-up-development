# Generated by Django 4.0.4 on 2024-12-27 01:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0027_alter_paymentlog_reason_alter_reviewquestion_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('OTHER', 'OTHER'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'), ('MYSTERY SHOP', 'MYSTERY SHOP')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='reviewquestion',
            name='type',
            field=models.CharField(blank=True, choices=[('DROPDOWN', 'DROPDOWN'), ('TEXTFIELD', 'TEXTFIELD'), ('YES_NO', 'YES_NO'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('OTHER', 'OTHER'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'), ('MYSTERY SHOP', 'MYSTERY SHOP')], max_length=255, null=True),
        ),
    ]
