# Generated by Django 4.0.4 on 2023-10-06 16:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0013_transactionpaymentlog_pp_campaign_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('OTHER', 'OTHER'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'), ('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='reviewquestion',
            name='type',
            field=models.CharField(blank=True, choices=[('TEXTFIELD', 'TEXTFIELD'), ('YES_NO', 'YES_NO'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE'), ('DROPDOWN', 'DROPDOWN')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('OTHER', 'OTHER'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'), ('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON')], max_length=255, null=True),
        ),
    ]
