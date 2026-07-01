from django import forms
from django.contrib.auth.models import Group, User

from progress.models import ProgressReport, Skill


class ProgressReportForm(forms.ModelForm):
    class Meta:
        model = ProgressReport
        fields = ['student', 'rating', 'skill', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        student_group = Group.objects.filter(name='student').first()
        if student_group:
            self.fields['student'].queryset = User.objects.filter(groups=student_group)
        else:
            self.fields['student'].queryset = User.objects.none()
        self.fields['skill'].queryset = Skill.objects.all()
        self.fields['skill'].required = False
