from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils.translation import gettext_lazy as _

from dashboard.models import RegistrationRequest, ContentManagerRegistration
from MakerPom.models import CreatPom

User = get_user_model()


class PoemEditForm(forms.ModelForm):
    """Allows content managers to edit a poem's title and text."""

    class Meta:
        model = CreatPom
        fields = ['name', 'text']
        labels = {
            'name': _('Poem Name'),
            'text': _('Poem Text'),
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'text': forms.Textarea(attrs={'class': 'form-control', 'rows': 10}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or not name.strip():
            raise forms.ValidationError(_('Poem name cannot be empty.'))
        return name.strip()

    def clean_text(self):
        text = self.cleaned_data.get('text')
        if not text or not text.strip():
            raise forms.ValidationError(_('Poem text cannot be empty.'))
        return text.strip()


class AudioReplaceForm(forms.Form):
    """Allows content managers to replace the poem's audio file."""
    voies = forms.FileField(
        label=_('Audio File'),
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'audio/*'}),
        help_text=_('Supported formats: MP3, WAV, OGG, etc.'),
    )

    def clean_voies(self):
        audio = self.cleaned_data.get('voies')
        if audio:
            allowed_extensions = ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac']
            ext = audio.name.rsplit('.', 1)[-1].lower() if '.' in audio.name else ''
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    _('Unsupported file type. Allowed: %(extensions)s.') % {'extensions': ', '.join(allowed_extensions)}
                )
            max_size = 20 * 1024 * 1024
            if audio.size > max_size:
                raise forms.ValidationError(_('File size must be under 20 MB.'))
        return audio


class AccessRequestForm(forms.ModelForm):
    """Public form for visitors to request content manager access."""

    class Meta:
        model = RegistrationRequest
        fields = ['full_name', 'email', 'message']
        labels = {
            'full_name': _('Full Name'),
            'email': _('Email Address'),
            'message': _('Message (optional)'),
        }
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_('An account with this email already exists.'))
        if RegistrationRequest.objects.filter(email=email, status='pending').exists():
            raise forms.ValidationError(_('A pending request already exists for this email.'))
        return email


class ContentManagerRegistrationForm(forms.ModelForm):
    """
    Dashboard registration form.

    No username field is rendered or accepted.
    The username is taken from `request.user.username` by the view.
    """
    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
    )
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
    )
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = ContentManagerRegistration
        fields = ['phone']
        labels = {
            'phone': _('Phone Number'),
        }
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.password = make_password(self.cleaned_data['password1'])
        if commit:
            instance.save()
        return instance