# Generated by Django 4.0.4 on 2023-04-19 21:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_alter_stationdriver_table'),
        ('payments', '0006_alter_paymentlog_payment_method'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReviewDriver',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('review_date', models.DateField(auto_now=True, null=True)),
                ('additional_notes', models.TextField(blank=True, null=True)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewed_driver', to='accounts.employee')),
                ('reviewed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='reviewd_driver_by', to='accounts.employee')),
            ],
        ),
        migrations.CreateModel(
            name='ReviewQuestion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255)),
                ('type', models.CharField(blank=True, choices=[('TEXTFIELD', 'TEXTFIELD'), ('DROPDOWN', 'DROPDOWN'), ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE'), ('YES_NO', 'YES_NO')], max_length=255, null=True)),
                ('details', models.TextField(blank=True, null=True)),
                ('info', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='TransactionCampaign',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('transaction_id', models.CharField(max_length=255)),
                ('transaction_funding_source_id', models.CharField(max_length=255)),
                ('total_budget', models.FloatField(default=0)),
                ('api_key', models.CharField(blank=True, max_length=255, null=True)),
                ('active', models.BooleanField(default=True)),
                ('source', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TransactionPaymentTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tag', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='approval_note',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='approved',
            field=models.CharField(blank=True, choices=[('PENDING', 'PENDING'), ('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED')], default='PENDING', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='approved_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_by', to='accounts.employee'),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='email_used',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='reason',
            field=models.CharField(blank=True, choices=[('OTHER', 'OTHER'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON')], max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='rejection_reason',
            field=models.CharField(choices=[('REPEATED_PAYMENT', 'REPEATED_PAYMENT'), ('PAYMENT_TOO_HIGH', 'PAYMENT_TOO_HIGH'), ('INVALID_REWARD_REASON', 'INVALID_REWARD_REASON')], max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='reward_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='paymentlog',
            name='reward_status',
            field=models.CharField(blank=True, default='PENDING', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='tremendouscampaign',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='tremendouscampaign',
            name='api_key',
            field=models.CharField(max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='tremendouscampaign',
            name='source',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='paymentlog',
            name='payment_method',
            field=models.CharField(choices=[('GIFT_CARD', 'GIFT_CARD'), ('WINGSPAN_API', 'WINGSPAN_API')], default='TREMENDOUS_API', max_length=255),
        ),
        migrations.CreateModel(
            name='WingSpanUserEmployee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('wingspanUserId', models.CharField(max_length=100)),
                ('type', models.CharField(max_length=100, null=True)),
                ('onboarded', models.BooleanField(default=False)),
                ('collaborator_id', models.CharField(blank=True, max_length=255, null=True)),
                ('production', models.BooleanField(default=True)),
                ('date_created', models.DateField(auto_now_add=True, null=True)),
                ('date_onboarded', models.DateField(blank=True, null=True)),
                ('employee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='wingspan_driver', to='accounts.employee')),
            ],
        ),
        migrations.CreateModel(
            name='TransactionPaymentLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_on', models.DateTimeField(auto_created=True, auto_now_add=True)),
                ('payment_method', models.CharField(choices=[('GIFT_CARD', 'GIFT_CARD'), ('WINGSPAN_API', 'WINGSPAN_API')], default='WINGSPAN_API', max_length=255)),
                ('payment_amount', models.FloatField(default=0)),
                ('notes', models.TextField(blank=True, null=True)),
                ('reason', models.CharField(blank=True, choices=[('OTHER', 'OTHER'), ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'), ('MYSTERY SHOP', 'MYSTERY SHOP'), ('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON')], max_length=255, null=True)),
                ('invoice_number', models.CharField(blank=True, max_length=255, null=True)),
                ('reward_status', models.CharField(blank=True, default='PENDING', max_length=255, null=True)),
                ('email_used', models.TextField(blank=True, null=True)),
                ('approved', models.CharField(blank=True, choices=[('PENDING', 'PENDING'), ('APPROVED', 'APPROVED'), ('REJECTED', 'REJECTED')], default='PENDING', max_length=255, null=True)),
                ('approval_note', models.TextField(blank=True, null=True)),
                ('rejection_reason', models.CharField(choices=[('REPEATED_PAYMENT', 'REPEATED_PAYMENT'), ('PAYMENT_TOO_HIGH', 'PAYMENT_TOO_HIGH'), ('INVALID_REWARD_REASON', 'INVALID_REWARD_REASON')], max_length=255, null=True)),
                ('transaction_id', models.CharField(blank=True, max_length=255, null=True)),
                ('approved_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transaction_approved_by', to='accounts.employee')),
                ('payment_from', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transaction_from', to='accounts.employee')),
                ('payment_to', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transaction_to', to='accounts.employee')),
                ('transaction_campaign', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_log_transaction_campaign', to='payments.transactioncampaign')),
                ('transaction_tag', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transaction_payment_tag', to='payments.transactionpaymenttag')),
            ],
        ),
        migrations.CreateModel(
            name='TransactionManagerBudget',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.FloatField(default=0)),
                ('manager', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transaction_manager_budget', to='accounts.employee')),
                ('transaction_campaign', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='manager_budget_transaction_campaign', to='payments.transactioncampaign')),
            ],
        ),
        migrations.CreateModel(
            name='ReviewForm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('questions', models.ManyToManyField(related_name='form_questions', to='payments.reviewquestion')),
            ],
        ),
        migrations.CreateModel(
            name='ReviewDriverQuestion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('answer', models.TextField(blank=True, null=True)),
                ('question', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='payments.reviewquestion')),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='payments.reviewdriver')),
            ],
        ),
        migrations.CreateModel(
            name='QueueUpPaymentEmail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sent', models.BooleanField(default=False)),
                ('date_sent', models.DateField(blank=True, null=True)),
                ('queue_created', models.DateField(auto_now_add=True)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='queue_payment_email', to='payments.transactionpaymentlog')),
            ],
        ),
    ]
