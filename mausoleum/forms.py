from django import forms
# from .models import Deceased, User, Image, Video


# class ImageForm(forms.ModelForm):
#     image_file = forms.FileField(required=True)
#     event_title = forms.CharField(required=True, max_length=100)
#     description = forms.CharField(required=True, max_length=255, widget=forms.Textarea)

#     class Meta:
#         model = Image
#         fields = ['image_file', 'event_title', 'description']

class ImageForm(forms.Form):
    image_file = forms.FileField(required=True)
    event_title = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea)

# class VideoForm(forms.ModelForm):
#     video_file = forms.FileField(required=True)
#     event_title = forms.CharField(required=True, max_length=100)
#     description = forms.CharField(required=True, max_length=255, widget=forms.Textarea)

#     class Meta:
#         model = Video
#         fields = ['video_file', 'event_title', 'description']


class VideoForm(forms.Form):
    video_file = forms.FileField(required=True)
    event_title = forms.CharField(max_length=100)
    description = forms.CharField(widget=forms.Textarea)


# class UserForm(forms.ModelForm):
#     class Meta:
#         model = User
#         fields = '__all__'

class UserForm(forms.Form):
    id_user = forms.IntegerField(required=False)
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=100)
    password = forms.CharField(widget=forms.PasswordInput, label='Password')


# class DeceasedForm(forms.ModelForm):
#     class Meta:
#         model = Deceased
#         fields = ['name', 'date_birth', 'date_death', 'description', 'burial_place']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
#             'date_birth': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'border rounded p-2 w-full'}),
#             'date_death': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'border rounded p-2 w-full'}),
#             'description': forms.Textarea(attrs={'class': 'border rounded p-2 w-full', 'rows': 3}),
#             'burial_place': forms.TextInput(attrs={'class': 'border rounded p-2 w-full'}),
#         }

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
