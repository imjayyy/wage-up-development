# Generated by Django 4.0.4 on 2024-12-14 00:20

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('performance_points', '0017_ppcampaign_show_performance_metrics_and_more'),
        ('training', '0004_moduletag_campaign'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='moduletag',
            name='campaign',
        ),
        migrations.AddField(
            model_name='moduleoverview',
            name='campaign',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaign_module_overviews', to='performance_points.ppcampaign'),
        ),
        migrations.AlterField(
            model_name='campaign',
            name='module',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns', to='training.moduleoverview'),
        ),
    ]
