from django.shortcuts import redirect
from django.urls import reverse

def login_required_auth0(view_func):
    def wrapper(request, *args, **kwargs):
        if 'user' not in request.session:
            return redirect(reverse('auth0_login'))
        return view_func(request, *args, **kwargs)
    return wrapper
