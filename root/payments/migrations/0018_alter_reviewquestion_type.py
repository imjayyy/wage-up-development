# Generated by Django 4.0.4 on 2024-12-13 22:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0017_alter_paymentlog_reason_alter_reviewquestion_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reviewquestion',
            name='type',
            field=models.CharField(blank=True, choices=[('DROPDOWN', 'DROPDOWN'), ('TEXTFIELD', 'TEXTFIELD'), ('YES_NO', 'YES_NO'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE')], max_length=255, null=True),
        ),
    ]
