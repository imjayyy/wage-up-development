# Generated by Django 4.0.4 on 2023-05-22 18:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_customwageupemail_active'),
        ('performance_points', '0006_remove_ppcampaignpointsbreakdown_employee'),
    ]

    operations = [
        migrations.AddField(
            model_name='ppcampaignpointsbreakdown',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_points_breakdown_employee', to='accounts.employee'),
        ),
    ]
