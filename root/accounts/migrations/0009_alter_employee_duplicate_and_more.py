# Generated by Django 4.0.4 on 2022-11-10 17:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_auto_20210623_1259'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='duplicate',
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='employee',
            name='fleet_supervisor',
            field=models.ManyToManyField(blank=True, to='accounts.employee'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='parallel_parents',
            field=models.ManyToManyField(blank=True, to='accounts.organization'),
        ),
    ]
