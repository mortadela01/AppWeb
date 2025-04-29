from django import forms
from .models import Deceased, User
from .models import Image, Video

class ImageForm(forms.ModelForm):
    image_file = forms.FileField(required=True)
    event_title = forms.CharField(required=True, max_length=100)
    description = forms.CharField(required=True, max_length=255, widget=forms.Textarea)

    class Meta:
        model = Image
        fields = ['image_file', 'event_title', 'description']

class VideoForm(forms.ModelForm):
    video_file = forms.FileField(required=True)
    event_title = forms.CharField(required=True, max_length=100)
    description = forms.CharField(required=True, max_length=255, widget=forms.Textarea)

    class Meta:
        model = Video
        fields = ['video_file', 'event_title', 'description']

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = '__all__'

class LoginForm(forms.Form):
    email = forms.EmailField(label='Correo electrónico', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput, label='Contraseña')

class DeceasedForm(forms.ModelForm):
    class Meta:
        model = Deceased
        fields = ['name', 'date_born', 'date_death', 'description', 'burial_place']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
            'date_born': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'border rounded p-2 w-full'}),
            'date_death': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'border rounded p-2 w-full'}),
            'description': forms.Textarea(attrs={'class': 'border rounded p-2 w-full', 'rows': 3}),
            'burial_place': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
        }

class ShareDeceasedForm(forms.Form):
    email = forms.EmailField(
        label="Email of the user to share with",
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@example.com',
            'class': 'border rounded p-2 w-full'
        })
    )
