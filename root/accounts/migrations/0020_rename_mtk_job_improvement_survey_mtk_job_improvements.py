# Generated by Django 4.0.4 on 2024-12-13 22:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_alter_survey_mtk_improvement_response_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='survey',
            old_name='mtk_job_improvement',
            new_name='mtk_job_improvements',
        ),
    ]
