from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from accounts.models import CustomUser
from dashboard.models import LoginAttempt

User = get_user_model()


class CustomLoginForm(forms.Form):
    username = forms.CharField(
        label=_('Username'),
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Username')})
    )
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': _('Password')})
    )

    user_cache = None
    request = None

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if username and password:
            ip = self.get_client_ip()
            if LoginAttempt.is_blocked(username, ip):
                raise forms.ValidationError(
                    _('Too many failed login attempts. Please try again later.')
                )
            user = authenticate(self.request, username=username, password=password)
            if user is None:
                raise forms.ValidationError(_('Invalid username or password.'))
            if not user.is_active:
                raise forms.ValidationError(_('This account has been deactivated.'))
            self.user_cache = user
        return cleaned_data

    def get_client_ip(self):
        if self.request:
            xff = self.request.META.get('HTTP_X_FORWARDED_FOR')
            if xff:
                return xff.split(',')[0].strip()
            return self.request.META.get('REMOTE_ADDR', '0.0.0.0')
        return '0.0.0.0'

    def get_user(self):
        return self.user_cache


class CustomUserCreationForm(UserCreationForm):
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label=_('Password Confirmation'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )


    class Meta:
        model = User
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) 
        for field_name in self.fields:
            self.fields[field_name].widget.attrs['class'] = 'form-control'
        

    def clean_face_image(self):
        image = self.cleaned_data.get('face_image')
        if image:
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('Face image must be under 5 MB.'))
            if not image.content_type.startswith('image/'):
                raise forms.ValidationError(_('Uploaded file is not a valid image.'))
        return image


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["username", 'first_name', 'last_name', 'email', 'avatar']
        labels = {
            "username": _("username"),
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class DashboardRequestForm(forms.Form):
    full_name = forms.CharField(
        max_length=200,
        label=_('Full Name'),
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    message = forms.CharField(
        label=_('Message (optional)'),
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.fields['full_name'].initial = self.user.get_full_name() or self.user.username
            self.fields['email'].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user and email != self.user.email:
            raise forms.ValidationError(_('Email does not match your account.'))
        return email


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Enter your email')}),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user = User.objects.filter(email=email).first()
        if not user:
            raise forms.ValidationError(_('No account found with this email address.'))
        return email


class SetNewPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        min_length=8,
    )
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1')
        p2 = cleaned_data.get('new_password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_('Passwords do not match.'))
        return cleaned_data