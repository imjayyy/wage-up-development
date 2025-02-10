from django import forms
from .models import UserDocument

class UserDocumentForm(forms.ModelForm):
    position_type = forms.MultipleChoiceField(choices=(
                ('------', ''),
                ('Driver', 'Driver'),
                ('Executive', 'Executive'),
                ('Station-Admin', 'Station-Admin'),
                ('Fleet-Manager', 'Fleet-Manager'),
                ('Call-Center-Operator', 'Call-Center-Operator'),
                ('Admin', 'Admin'),
                ('Territory-Associate', 'Territory-Associate')
            ))

    class Meta:
        model = UserDocument
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(UserDocumentForm, self).__init__(*args, **kwargs)
        try:
            model_instance = kwargs['instance']
            if model_instance.position_type is not None:
                positions = model_instance.position_type.split(', ')
            else:
                positions = []
            self.initial['position_type'] = positions
        except:
            pass

