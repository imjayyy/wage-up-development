# Generated by Django 2.1.4 on 2021-06-23 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_auto_20210609_1656'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='group',
            field=models.ManyToManyField(blank=True, related_name='employee_group', to='accounts.EmployeeGroup'),
        ),
        migrations.AlterField(
            model_name='employee',
            name='parallel_organizations',
            field=models.ManyToManyField(blank=True, related_name='employee_parallel_organization', to='accounts.Organization'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='parallel_parents',
            field=models.ManyToManyField(blank=True, related_name='_organization_parallel_parents_+', to='accounts.Organization'),
        ),
    ]
