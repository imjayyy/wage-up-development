# Generated by Django 4.0.4 on 2023-10-13 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_rename_driver_aca_id_eligibledriver_driver_id_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='survey',
            name='mtk_improvement_response',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='survey',
            name='mtk_testimonial',
            field=models.TextField(blank=True, null=True),
        ),
    ]
