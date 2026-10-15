# MakePom/forms.py
from django import forms
from MakerPom.models import CreatPom
from django.utils.translation import gettext_lazy as _

class CreatePomForm(forms.ModelForm): 
    class Meta:
        model = CreatPom
        fields = ['name', 'text', "poem_type", "voies"]
        labels = {
            "name": _("Poem Name"),
            "text": _("Poem Text"),
            "voies": _("Select Voice"),
            "poem_type": _("Poem Type"),
        }