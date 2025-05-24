from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps

def login_required_auth0(view_func):
    def wrapper(request, *args, **kwargs):
        if 'user' not in request.session:
            return redirect(reverse('auth0_login'))
        return view_func(request, *args, **kwargs)
    return wrapper


def login_required_custom(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'user' not in request.session or 'access_token' not in request.session['user']:
            return redirect('auth0_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view