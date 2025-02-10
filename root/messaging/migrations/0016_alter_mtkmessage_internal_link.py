# Generated by Django 4.0.4 on 2024-12-27 01:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0015_alter_mtkmessage_banner_text'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mtkmessage',
            name='internal_link',
            field=models.CharField(blank=True, choices=[('/campaigns', '/campaigns'), ('/payments', '/payments'), ('/training', '/training')], max_length=255, null=True),
        ),
    ]
