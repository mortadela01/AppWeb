from django.shortcuts import redirect

def login_required_auth0(view_func):
    def wrapper(request, *args, **kwargs):
        if 'user' not in request.session:
            return redirect('login_auth0')
        return view_func(request, *args, **kwargs)
    return wrapper
