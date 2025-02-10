from django.db import models
from django.contrib.auth.models import User
from accounts.models import Permissions, Employee, Organization
from django.utils import timezone

# what is the module?
class QuestionsAnswer(models.Model):
    answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    question = models.ForeignKey('ModuleQuestion', null=True, blank=True, on_delete=models.CASCADE, related_name='answers')

class ModuleQuestion(models.Model):
    question = models.CharField(max_length=255)
    page = models.ForeignKey('ModulePage', null=True, blank=True, on_delete=models.CASCADE, related_name='page_questions')
    type = models.CharField(max_length=255, choices=(
        ('multiple_choice', 'multiple_choice'),
        ('true_false', 'true_false'),
        ('open_ended', 'open_ended')
    ), null=True, blank=True)

class ModulePage(models.Model):
    type = models.CharField(max_length=255, choices=(
        ('questions', 'questions'),
        ('audio', 'audio'),
        ('video', 'video')
    ), null=True, blank=True)
    media_link = models.CharField(max_length=255, null=True, blank=True)
    overview = models.ForeignKey('ModuleOverview', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='overview_pages')
    media_length_required = models.IntegerField(null=True, blank=True)

class ModuleTag(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)

class ModuleOverview(models.Model):
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    icon = models.URLField(null=True, blank=True)
    question_count = models.IntegerField(null=True, blank=True)
    pass_threshold = models.FloatField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True, auto_now_add=True)
    active = models.BooleanField(default=True)
    creator = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    campaign = models.ForeignKey('performance_points.ppcampaign', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='campaign_module_overviews')

    def __str__(self):
        return str(self.title)

    def get_event_count(self):
        return ModuleFlow.objects.filter(module=self.id).count()

class ModuleCompletion(models.Model):
    module = models.ForeignKey(ModuleOverview, null=True, blank=True, on_delete=models.SET_NULL, related_name='module_completion')
    employee = models.ForeignKey(Employee, blank=True, null=True, on_delete=models.SET_NULL, related_name='employee_module_completions')
    completed = models.BooleanField(default=False)
    date_completed = models.DateField(null=True, blank=True)
    last_completed_page = models.ForeignKey(ModulePage, null=True, blank=True, on_delete=models.SET_NULL, related_name='module_completion_page')

class Campaign(models.Model):
    title = models.CharField(max_length=255)
    module = models.ForeignKey(ModuleOverview, null=True, blank=True, on_delete=models.SET_NULL, related_name='campaigns')
    start = models.DateField(null=True, blank=True)
    end = models.DateField(null=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.title)

class CampaignUser(models.Model):
    campaign = models.ForeignKey(Campaign, blank=True, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    employee = models.ForeignKey(Employee, blank=True, null=True, on_delete=models.SET_NULL)
    reward = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    updated = models.DateTimeField(null=True, blank=True, default=timezone.now)

# questions and answers
class ModuleMultipleChoice(models.Model):
    question = models.TextField(null=True, blank=True)
    answer_one = models.TextField(null=True, blank=True)
    answer_two = models.TextField(null=True, blank=True)
    answer_three = models.TextField(null=True, blank=True)
    answer_four = models.TextField(null=True, blank=True)
    answer_five = models.TextField(null=True, blank=True)
    correct_answer = models.IntegerField(null=True, blank=True)
    module = models.ForeignKey(ModuleOverview, null=True, blank=True, on_delete=models.SET_NULL, related_name='training_multiple_choice')
    answer_explanation = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.question)

# module flow
class ModuleFlow(models.Model):
    module = models.ForeignKey(ModuleOverview, null=True, blank=True, on_delete=models.SET_NULL, related_name='training_module_flow')
    event_order = models.IntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=255, null=True, blank=True)
    html_text = models.TextField(null=True, blank=True)
    video = models.URLField(null=True, blank=True)
    multiple_choice = models.ForeignKey(ModuleMultipleChoice, null=True, blank=True, on_delete=models.SET_NULL, related_name='training_module_flow')

    def __str__(self):
        return str(self.module.title)

# users progress so far
class UserProgress(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, related_name='training_progress', on_delete=models.SET_NULL)
    module = models.ForeignKey(ModuleOverview, null=True, blank=True, on_delete=models.SET_NULL, related_name='training_progress')
    last_event = models.ForeignKey(ModuleFlow, null=True, blank=True, on_delete=models.SET_NULL, related_name='training_progress')
    correct_questions = models.IntegerField(blank=True, null=True)
    incorrect_questions = models.IntegerField(blank=True, null=True)
    passed = models.BooleanField(null=True)
    final_grade = models.FloatField(null=True, blank=True)
    question_history = models.TextField(blank=True, null=True)
    updated = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return str(self.user.username) + ": " + str(self.module.title)

    def get_organization(self):
        try:
            employee = Employee.objects.get(user=self.user)
            organization = Organization.objects.get(id=employee.organization.id)
            station = Organization.objects.get(id=employee.default_station)
            return {'facility': organization.name,
                    'territory': organization.get_parent_to('Territory').name,
                    'station': station.name}
        except:
            return None

# employees and other coursework

# class EmployeeCoursework(models.Model):
#     Employee = models.ForeignKey(Employee, null=True, blank=True, related_name='training_progress', on_delete=models.SET_NULL)

class UserDocumentCategory(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255)

    def __str__(self):
        return self.name

class UserDocument(models.Model):
    doc_name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=100)
    doc_url = models.CharField(max_length=255)
    doc_desc = models.TextField(null=True, blank=True)
    thumbnail = models.ImageField(upload_to='documents/thumbnails/', blank=True, null=True)
    permission = models.ForeignKey(Permissions, null=True, blank=True, on_delete=models.SET_NULL)
    position_type = models.CharField(max_length=255, null=True, blank=True)
    facility_type = models.CharField('Driver Type', max_length=255, null=True, blank=True, choices=(
        ('All', 'All'),
        ('CSN', 'CSN'),
        ('Fleet', 'Fleet')
    ))
    category = models.ForeignKey(UserDocumentCategory, null=True, blank=True, on_delete=models.SET_NULL)
    active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.doc_name)

    def create_thumbnail(self):
        if not self.thumbnail:
            return

        from PIL import Image
        from io import BytesIO, StringIO
        from django.core.files.uploadedfile import InMemoryUploadedFile

        image = Image.open(BytesIO(self.thumbnail.read()))
        image.thumbnail((150, 150), Image.ANTIALIAS)
        output = BytesIO()
        image.save(output, format='JPEG', quality=75)
        output.seek(0)
        self.thumbnail = InMemoryUploadedFile(output, 'ImageField', '{0}.jpg'.format(self.thumbnail.name), 'image/jpeg', output.getbuffer().nbytes, None)

        # thumbnail_size = (150, 150)
        # image = Image.open(self.thumbnail)
        # print(image.format)
        # image_type = image.format
        #
        # if image_type == 'JPEG':
        #     pil_type = 'jpeg'
        #     extention = 'jpg'
        # if image_type == 'PNG':
        #     pil_type = 'png'
        #     extention = 'png'
        #
        #
        # image.thumbnail(thumbnail_size, Image.ANTIALIAS)
        # temp_handle = StringIO()
        # image.save(temp_handle, pil_type)
        # temp_handle.seek(0)
        # suf = SimpleUploadedFile(self.thumbnail.name, temp_handle.read(), content_type=extention)
        # self.thumbnail.save(self.thumbnail.name, extention, suf, save=False)

    def save(self, *args, **kwargs):
        if self.thumbnail:
            self.create_thumbnail()
        super(UserDocument, self).save(*args, **kwargs)

class TrainingProgress(models.Model):
    passed = models.BigIntegerField(null=True, blank=True)
    final_grade = models.FloatField(null=True, blank=True)
    module = models.CharField(max_length=255, blank=True, null=True)
    last_updated = models.DateTimeField()
    first_name= models.CharField(max_length=255, blank=True, null=True)
    last_name= models.CharField(max_length=255, blank=True, null=True)
    position_type= models.CharField(max_length=255, blank=True, null=True)
    d3_login_id= models.CharField(max_length=255, blank=True, null=True)
    no_login_id_match = models.BooleanField(null=True)
    organization_name= models.CharField(max_length=255, blank=True, null=True)
    organization_parent_name= models.CharField(max_length=255, blank=True, null=True)
    percent_complete = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = 'training_results_more'

class TrainingVideo(models.Model):
    name = models.CharField(max_length=255)
    video_url = models.CharField(max_length=255)
    display_start = models.DateField(null=True, blank=True)
    display_end = models.DateField(null=True, blank=True)
    completed_list = models.ManyToManyField(Employee)

class TrainingVideoQuestion(models.Model):
    video_ref = models.ForeignKey(TrainingVideo, on_delete=models.CASCADE, related_name='video_reference')
    question = models.TextField()
    correct = models.ManyToManyField(Employee, related_name='completed_and_correct')
    incorrect = models.ManyToManyField(Employee, related_name='completed_and_incorrect')

class TrainingViedoQuestionAnswer(models.Model):
    question = models.ForeignKey(TrainingVideoQuestion, on_delete=models.CASCADE, null=True, blank=True, related_name='possible_answer')
    answer = models.CharField(max_length=255)
    correct = models.BooleanField(default=False)

class ShoutOut(models.Model):
    driver = models.CharField(max_length=255)
    station = models.CharField(max_length=255)
    quote = models.TextField()
    image = models.FileField(null=True, blank=True)