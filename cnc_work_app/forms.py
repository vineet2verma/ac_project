from django import forms
from .models import MachineMaster, MachineDetail

class MachineForm(forms.ModelForm):
    class Meta:
        model = MachineMaster
        fields = ["machine_no", "machine_name", "remarks"]




class MachineDetailForm(forms.ModelForm):
    class Meta:
        model = MachineDetail
        fields = ["machine_name", "working_hour", "operator", "remarks"]

        widgets = {
            "machine_name": forms.Select(
                attrs={
                    "class": "form-control",
                    "required": True,
                }
            ),
            "working_hour": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.1",
                    "required": True,
                }
            ),
            "operator": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Operator name",
                }
            ),
            "remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                }
            ),
        }