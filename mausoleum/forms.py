from django import forms

class ImageForm(forms.Form):
    image_file = forms.FileField(required=True)
    event_title = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea)

class VideoForm(forms.Form):
    video_file = forms.FileField(required=True)
    event_title = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea)

class UserForm(forms.Form):
    id_user = forms.IntegerField(required=False)
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)

class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput, label='Password')


class DeceasedForm(forms.Form):
    name = forms.CharField(max_length=100)
    date_birth = forms.DateTimeField(required=False)
    date_death = forms.DateTimeField(required=False)
    description = forms.CharField(required=False, widget=forms.Textarea)
    burial_place = forms.CharField(max_length=100, required=False)


class ShareDeceasedForm(forms.Form):
    email = forms.EmailField(
        label="Email of the user to share with",
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@example.com',
            'class': 'border rounded p-2 w-full'
        })
    )
