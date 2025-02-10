from django.db import models
from accounts.models import *
from performance_points.models import PPCampaign, PPCampaignPaymentPeriod

# Create your models here.
from django.db.models import Sum

PAYMENT_METHODS = {
    ("GIFT_CARD", "GIFT_CARD"),
    ('WINGSPAN_API', 'WINGSPAN_API')
}

BUDGET_PERIODS = {
    ("ANNUAL", "ANNUAL"),
    ("MONTHLY", "MONTHLY"),
    ("DAILY", "DAILY"),
    ("ALL_TIME", "ALL_TIME")
}

REASON_FOR_PAYMENT = {
    ('GREAT JOB - IN PERSON', 'GREAT JOB - IN PERSON'),
    ('GREAT JOB - REMOTE', 'GREAT JOB - REMOTE'),
    ('MYSTERY SHOP', 'MYSTERY SHOP'),
    ('OTHER', 'OTHER')
}

class RaffleWinners(models.Model):
    user = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='raffle_winner')
    date_won = models.DateField(auto_now_add=True)

class RaffleEntry(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='raffle_entry')
    date_entered = models.DateField(auto_now_add=True)
    reason = models.CharField(max_length=255, null=True, blank=True)
    campaign = models.ForeignKey(PPCampaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='raffle_entry_campaign')

class TransactionCampaign(models.Model):
    name = models.CharField(max_length=255)
    transaction_id = models.CharField(max_length=255)
    transaction_funding_source_id = models.CharField(max_length=255)
    total_budget = models.FloatField(default=0)
    api_key = models.CharField(max_length=255, null=True, blank=True)
    active = models.BooleanField(default=True)
    source = models.BooleanField(default=False)

    def get_remaining_budget(self):
        return self.total_budget - PaymentLog.objects.filter(trenemdous_campaign_id = self.id).aggregate(total_paid=Sum('payment_amount'))['total_paid']

    def __str__(self):
        return self.name

class TremendousCampaign(models.Model):
    name = models.CharField(max_length=255)
    tremendous_id = models.CharField(max_length=255)
    tremendous_funding_source_id = models.CharField(max_length=255)
    total_budget = models.FloatField(default=0)
    api_key = models.CharField(max_length=500, null=True)
    active = models.BooleanField(default=True)
    source = models.BooleanField(default=False)

    def get_remaining_budget(self):
        return self.total_budget - PaymentLog.objects.filter(trenemdous_campaign_id = self.id).aggregate(total_paid=Sum('payment_amount'))['total_paid']

    def __str__(self):
        return self.name

# class TransactionConnection(models.Model):
#     collaborator = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payment_payer')
#     client = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='payment_payee')
#     collaborator_id = models.CharField(max_length=255, null=True, blank=True)
#
#     def __str__(self):
#         return f'{self.payment_from.full_name} paying {self.payment_to.full_name}'

class TransactionPaymentTag(models.Model):
    tag = models.CharField(max_length=255)

    def __str__(self):
        return self.tag

class TransactionPaymentLog(models.Model):
     payment_from = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='transaction_from')
     payment_to = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='transaction_to')
     payment_method = models.CharField(max_length=255, choices=PAYMENT_METHODS, default='WINGSPAN_API')
     payment_amount = models.FloatField(default=0)
     notes = models.TextField(null=True, blank=True)
     created_on = models.DateTimeField(auto_created=True, auto_now_add=True)
     transaction_campaign = models.ForeignKey(TransactionCampaign, null=True, blank=True, on_delete=models.SET_NULL, related_name='payment_log_transaction_campaign')
     reason = models.CharField(max_length=255, null=True, blank=True, choices=REASON_FOR_PAYMENT)
     invoice_number = models.CharField(max_length=255, null=True, blank=True)
     reward_status = models.CharField(max_length=255, null=True, blank=True, default='PENDING')
     email_used = models.TextField(null=True, blank=True)
     approved = models.CharField(max_length=255, null=True,
                                blank=True,
                                choices=[('PENDING', 'PENDING'), ('APPROVED', 'APPROVED'),('REJECTED', 'REJECTED')],
                                default='PENDING')
     approval_note = models.TextField(null=True, blank=True)
     rejection_reason = models.CharField(max_length=255,
                                        choices=[('REPEATED_PAYMENT', 'REPEATED_PAYMENT'),
                                                 ('PAYMENT_TOO_HIGH', 'PAYMENT_TOO_HIGH'),
                                                 ('INVALID_REWARD_REASON', 'INVALID_REWARD_REASON')],
                                        null=True)
     approved_by = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='transaction_approved_by')
     transaction_tag = models.ForeignKey(TransactionPaymentTag, null=True, on_delete=models.SET_NULL, related_name='transaction_payment_tag')
     transaction_id = models.CharField(max_length=255, null=True, blank=True)
     pp_campaign = models.ForeignKey(PPCampaign, null=True, on_delete=models.SET_NULL, blank=True, related_name='performance_points_campaign')
     pp_campaign_pay_period = models.ForeignKey(PPCampaignPaymentPeriod, on_delete=models.SET_NULL, null=True, blank=True, related_name='performance_points_campaign_pay_period')

     def __str__(self):
         return f"{self.payment_from} -> {self.payment_to} : {self.payment_amount}"

class PaymentLog(models.Model):
    payment_from = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='payment_from')
    payment_to = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='payment_to')
    payment_method = models.CharField(
        max_length=255,
        choices=PAYMENT_METHODS,
        default="TREMENDOUS_API",
    )
    notes = models.TextField(null=True, blank=True)
    created_on = models.DateTimeField(auto_created=True, auto_now_add=True)
    payment_amount = models.FloatField(default=0)
    # transaction_campaign = models.ForeignKey(TransactionCampaign, null=True, blank=True, on_delete=models.SET_NULL, related_name='payment_log_transaction_campaign')
    tremendous_campaign = models.ForeignKey(TremendousCampaign, null=True, on_delete=models.SET_NULL, related_name='payment_log_tremendous_campaign')
    reason = models.CharField(max_length=255, null=True, blank=True, choices=REASON_FOR_PAYMENT)
    reward_id = models.CharField(max_length=255, null=True, blank=True)
    reward_status = models.CharField(max_length=255, null=True, blank=True, default='PENDING')
    email_used = models.TextField(null=True, blank=True)
    approved = models.CharField(max_length=255, null=True,
                                blank=True,
                                choices=[('PENDING', 'PENDING'), ('APPROVED', 'APPROVED'),('REJECTED', 'REJECTED')],
                                default='PENDING')
    approval_note = models.TextField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255,
                                        choices=[('REPEATED_PAYMENT', 'REPEATED_PAYMENT'),
                                                 ('PAYMENT_TOO_HIGH', 'PAYMENT_TOO_HIGH'),
                                                 ('INVALID_REWARD_REASON', 'INVALID_REWARD_REASON')],
                                        null=True)
    approved_by = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='approved_by')
#     note for reason for payment
    def __str__(self):
        return f"{self.payment_from} -> {self.payment_to} : {self.payment_amount}"

class TransactionManagerBudget(models.Model):
    manager = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='transaction_manager_budget')
    amount = models.FloatField(default=0)
    transaction_campaign = models.ForeignKey(TransactionCampaign, null=True, on_delete=models.SET_NULL, related_name='manager_budget_transaction_campaign')

    def save(self, *args, **kwargs):
        manager_budget = TransactionManagerBudget.objects.filter(transaction_campaign_id=self.transaction_campaign).aggregate(total_budget=Sum('amount'))['total_budget']
        if manager_budget is None:
            manager_budget = 0
        campaign_budget = float(TransactionCampaign.objects.get(id=self.transaction_campaign_id).total_budget)
        print(manager_budget, campaign_budget, self.amount)
        if (manager_budget + self.amount) > campaign_budget:
            raise Exception("Exceeds Budget Not allowed!")
        super(TransactionManagerBudget, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.manager.full_name} {self.transaction_campaign} {self.amount}"

class ManagerBudget(models.Model):
    manager = models.ForeignKey(Employee, null=True, on_delete=models.SET_NULL, related_name='manager_budget')
    amount = models.FloatField(default=0)
    tremendous_campaign = models.ForeignKey(TremendousCampaign, null=True, on_delete=models.SET_NULL, related_name='manager_budget_tremendous_campaign')

    def save(self, *args, **kwargs):
        manager_budget = ManagerBudget.objects.filter(tremendous_campaign_id=self.tremendous_campaign).aggregate(total_budget=Sum('amount'))['total_budget']
        if manager_budget is None:
            manager_budget = 0
        campaign_budget = float(TremendousCampaign.objects.get(id=self.tremendous_campaign_id).total_budget)
        print(manager_budget, campaign_budget, self.amount)
        if (manager_budget + self.amount) > campaign_budget:
            raise Exception("Exceeds Budget Not allowed!")
        super(ManagerBudget, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.manager.full_name} {self.tremendous_campaign} {self.amount}"

REVIEW_Q_TYPES = {
    ('TEXTFIELD', 'TEXTFIELD'),
    ('DROPDOWN', 'DROPDOWN'),
    ('MULTIPLE_CHOICE', 'MULTIPLE_CHOICE'),
    ('YES_NO', 'YES_NO'),
}

class ReviewQuestion(models.Model):
    question = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=REVIEW_Q_TYPES, null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    info = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'{self.question} ({self.type})'


class ReviewForm(models.Model):
    name = models.CharField(max_length=255)
    questions = models.ManyToManyField(ReviewQuestion, related_name='form_questions')

class ReviewDriver(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_driver')
    review_date = models.DateField(auto_now=True, null=True, blank=True)
    reviewed_by = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewd_driver_by')
    additional_notes = models.TextField(null=True, blank=True)

class ReviewDriverQuestion(models.Model):
    review = models.ForeignKey(ReviewDriver, on_delete=models.CASCADE)
    question = models.ForeignKey(ReviewQuestion, on_delete=models.SET_NULL, null=True, blank=True)
    answer = models.TextField(null=True, blank=True)


class WingSpanUserEmployee(models.Model):
    wingspanUserId = models.CharField(max_length=100)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, related_name='wingspan_driver')
    type = models.CharField(max_length=100, null=True)
    onboarded = models.BooleanField(default=False)
    collaborator_id = models.CharField(max_length=255, blank=True, null=True)
    production = models.BooleanField(default=True)
    date_created = models.DateField(auto_now_add=True, blank=True, null=True)
    date_onboarded = models.DateField(auto_now_add=False, auto_now=False, null=True, blank=True)
    completed_w9 = models.BooleanField(default=False)

    def need_w9(self):
        if self.completed_w9:
            return False
        else:
            total_awards = TransactionPaymentLog.objects.filter(payment_to_id=self.employee.id, payment_method='WINGSPAN_API')\
                .aggregate(total_awards=Sum('payment_amount'))['total_awards']
            print("TOTAL AWARDS", total_awards)
            return int(total_awards or 0) >= 600

class QueueUpPaymentEmail(models.Model):
    payment = models.ForeignKey(TransactionPaymentLog, on_delete=models.CASCADE, related_name='queue_payment_email')
    sent = models.BooleanField(default=False)
    date_sent = models.DateField(auto_now_add=False, auto_now=False, null=True, blank=True)
    queue_created = models.DateField(auto_now_add=True)

class WingSpanUserW9(models.Model):
    wingspanUserId = models.ForeignKey(WingSpanUserEmployee, on_delete=models.SET_NULL, null=True, blank=True, related_name='wingspan_driver')
    year = models.IntegerField()
    completed = models.BooleanField(default=False)
    date_completed = models.DateField(null=True, blank=True)

    def needs_w9(self):
        employee_id = self.wingspanUserId.employee.id
        payment_sum = TransactionPaymentLog.objects.filter(payment_to_id=employee_id, payment_method='WINGSPAN_API', created_on__year=self.year).aggregate(total=Sum('payment_amount'))['total']
        if payment_sum is not None and payment_sum >= 600:
            return not self.completed
        return False
