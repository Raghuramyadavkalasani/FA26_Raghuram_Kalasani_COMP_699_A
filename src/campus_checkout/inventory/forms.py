from django import forms
from .services import validate_interval

class IntervalForm(forms.Form):
    start = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}), help_text="America/New_York local time")
    end = forms.DateTimeField(widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    def clean(self):
        data = super().clean()
        if "start" in data and "end" in data:
            validate_interval(data["start"], data["end"])
        return data

class SearchForm(IntervalForm):
    q = forms.CharField(required=False, label="Equipment name or category")
