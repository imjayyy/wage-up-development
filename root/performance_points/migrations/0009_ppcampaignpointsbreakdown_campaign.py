# Generated by Django 4.0.4 on 2023-05-22 18:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('performance_points', '0008_remove_ppcampaignpointsbreakdown_campaign'),
    ]

    operations = [
        migrations.AddField(
            model_name='ppcampaignpointsbreakdown',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_points_breakdown_campaign', to='performance_points.ppcampaign'),
        ),
    ]
