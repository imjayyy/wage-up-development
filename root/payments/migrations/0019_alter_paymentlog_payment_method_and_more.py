# Generated by Django 4.0.4 on 2024-12-13 23:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0018_alter_reviewquestion_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paymentlog',
            name='payment_method',
            field=models.CharField(choices=[('GIFT_CARD', 'GIFT_CARD'), ('WINGSPAN_API', 'WINGSPAN_API')], default='TREMENDOUS_API', max_length=255),
        ),
        migrations.AlterField(
            model_name='paymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('OTHER', 'OTHER'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='reviewquestion',
            name='type',
            field=models.CharField(blank=True, choices=[('YES_NO', 'YES_NO'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE'), ('DROPDOWN', 'DROPDOWN'), ('TEXTFIELD', 'TEXTFIELD')], max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='payment_method',
            field=models.CharField(choices=[('GIFT_CARD', 'GIFT_CARD'), ('WINGSPAN_API', 'WINGSPAN_API')], default='WINGSPAN_API', max_length=255),
        ),
        migrations.AlterField(
            model_name='transactionpaymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'), ('OTHER', 'OTHER'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE')], max_length=255, null=True),
        ),
    ]
