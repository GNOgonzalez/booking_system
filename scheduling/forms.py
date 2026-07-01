from django import forms

from scheduling.models import AvailabilityBlock, ClassType, Session


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['class_type', 'title', 'start_time', 'end_time', 'capacity']
        widgets = {
            'start_time': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local'},
            ),
            'end_time': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local'},
            ),
        }

    def __init__(self, *args, teacher=None, **kwargs):
        super().__init__(*args, **kwargs)
        if teacher is not None:
            self.fields['class_type'].queryset = ClassType.objects.filter(
                teacher=teacher,
                is_active=True,
            )
        self.fields['class_type'].required = False


class AvailabilityBlockForm(forms.ModelForm):
    class Meta:
        model = AvailabilityBlock
        fields = ['weekday', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class ClassTypeForm(forms.ModelForm):
    class Meta:
        model = ClassType
        fields = ['name', 'description', 'default_capacity', 'is_active']
