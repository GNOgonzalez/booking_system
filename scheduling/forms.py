from django import forms

from scheduling.models import AvailabilityBlock, ClassOffering, Session, SpecialAvailability


class SessionForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = ['class_offering', 'start_time', 'end_time', 'capacity', 'meeting_provider']
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
            self.fields['class_offering'].queryset = ClassOffering.objects.filter(
                teacher=teacher,
                is_active=True,
            )
        self.fields['class_offering'].required = True


class AvailabilityBlockForm(forms.ModelForm):
    class Meta:
        model = AvailabilityBlock
        fields = ['weekday', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }


class SpecialAvailabilityForm(forms.ModelForm):
    class Meta:
        model = SpecialAvailability
        fields = ['date', 'start_time', 'end_time', 'note']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
        }
