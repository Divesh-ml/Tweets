from django import forms
from .models import Tweet
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class TweetForm(forms.ModelForm):
    class Meta:
        model = Tweet
        fields = ['text', 'photo']


class ReplyForm(forms.Form):
    text = forms.CharField(
        max_length=240,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Write a reply...',
        }),
    )


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label='Email address')

    class Meta:
        model = User
        fields = ('username','email','password1','password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Username'
        self.fields['username'].help_text = 'Choose a name to identify your account.'
        self.fields['password1'].label = 'Password'
        self.fields['password2'].label = 'Confirm password'
        self.fields['password2'].help_text = 'Enter the same password again.'
        self.fields['username'].widget.attrs.update(autocomplete='username')
        self.fields['email'].widget.attrs.update(autocomplete='email')
        self.fields['password1'].widget.attrs.update(autocomplete='new-password')
        self.fields['password2'].widget.attrs.update(autocomplete='new-password')
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'