# Generated by Django 2.1.4 on 2021-04-22 22:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('messaging', '0002_auto_20210415_1219'),
    ]

    operations = [
        migrations.AddField(
            model_name='announcements',
            name='link_external',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='announcements',
            name='link_text',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
