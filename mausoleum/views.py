import os
import re
import requests
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from .decorators import login_required_auth0, login_required_custom
from .forms import DeceasedForm, ShareDeceasedForm, ImageForm, VideoForm
from django.db import connection
from django.views.decorators.http import require_GET
from django.http import JsonResponse

from .api_client import APIClient
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt




# -------------------- AUTH0 --------------------

def auth0_login(request):
    params = {
        'client_id': settings.AUTH0_CLIENT_ID,
        'response_type': 'code',
        'scope': 'openid profile email',
        'redirect_uri': settings.AUTH0_CALLBACK_URL,
    }
    return redirect(f"https://{settings.AUTH0_DOMAIN}/authorize?" + urlencode(params))

def callback(request):
    code = request.GET.get('code')
    token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        'grant_type': 'authorization_code',
        'client_id': settings.AUTH0_CLIENT_ID,
        'client_secret': settings.AUTH0_CLIENT_SECRET,
        'code': code,
        'redirect_uri': settings.AUTH0_CALLBACK_URL,
    }

    token_info = requests.post(token_url, json=token_payload).json()
    user_url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
    headers = {'Authorization': f"Bearer {token_info['access_token']}"}
    user_info = requests.get(user_url, headers=headers).json()

    email = user_info.get('email')
    name = user_info.get('name', '')
    sub = user_info.get('sub', '')

    api_client = APIClient()

    # Consultar usuario en appServer, esperar que incluya token OAuth local
    response = api_client.get_user_by_email(email)

    if 'access_token' in response:
        # Guardar solo token local de appServer
        request.session['user'] = {
            'email': email,
            'name': name,
            'picture': user_info.get('picture'),
            'access_token': response['access_token'],
        }
    else:
        # Usuario no existe, crear y obtener token local
        user_data = {
            'name': name,
            'email': email,
            'password': sub
        }
        created_user = api_client.create_user(user_data)
        if created_user and 'access_token' in created_user:
            request.session['user'] = {
                'email': email,
                'name': name,
                'picture': user_info.get('picture'),
                'access_token': created_user['access_token'],
            }
        else:
            # No guardar token si no se obtiene token local
            # Podrías decidir redirigir a error o logout
            return redirect('auth0_logout')

    return redirect('dashboard')



def auth0_logout(request):
    request.session.flush()
    return redirect(f"https://{settings.AUTH0_DOMAIN}/v2/logout?" + urlencode({
        'client_id': settings.AUTH0_CLIENT_ID,
        'returnTo': 'http://localhost:8000'
    }))

# -------------------- DASHBOARD --------------------

# login_required_custom
@login_required_custom
def dashboard(request):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    api_response = api_client.get_dashboard()

    if 'user' in api_response:
        return render(request, 'dashboard.html', {
            'user': api_response['user'],
            'notifications': api_response.get('notifications', []),
            'unread_count': api_response.get('unread_count', 0),
        })
    else:
        # Token inválido o error, forzar logout
        return redirect('auth0_logout')


# -------------------- ADD FAMILY MEMBER --------------------

@login_required_custom
@csrf_exempt
def add_family_member(request):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        data = request.POST.dict()
        related = request.POST.getlist('related_deceased[]')
        types = request.POST.getlist('relationship_type[]')

        data['related_deceased'] = related
        data['relationship_type'] = types

        files_to_send = []
        for key, file_list in request.FILES.lists():
            for f in file_list:
                files_to_send.append((key, (f.name, f.read(), f.content_type)))

        # Usar base_url desde instancia api_client (opción recomendada)
        url = f"{api_client.base_url}/appweb/family-members/add/"

        headers = {
            'Authorization': f'Bearer {token}',
            # No incluir Content-Type, requests lo maneja con multipart/form-data
        }

        import requests
        resp = requests.post(
            url,
            headers=headers,
            data=data,
            files=files_to_send,
        )

        if resp.status_code == 201:
            return redirect('family_member_list')
        else:
            try:
                error_data = resp.json()
            except Exception:
                error_data = resp.text
            return render(request, 'add_family_member.html', {'error': error_data})

    else:
        deceased_list = api_client.list_deceased()
        return render(request, 'add_family_member.html', {'all_deceased': deceased_list})





# -------------------- FAMILY MEMBER LIST --------------------

@login_required_custom
def family_member_list(request):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    data = api_client.get_family_members()

    miembros = data.get('miembros', [])
    permisos = data.get('permisos', [])
    otros_deceased = data.get('otros_deceased', [])
    notifications = data.get('notifications', [])        # <-- Agregado
    unread_count = data.get('unread_count', 0)           # <-- Agregado

    return render(request, 'family_member_list.html', {
        'miembros': miembros,
        'permisos': permisos,
        'otros_deceased': otros_deceased,
        'notifications': notifications,       # <-- Pasar al template
        'unread_count': unread_count,         # <-- Pasar al template
    })



# -------------------- SHARE / EDIT / DELETE --------------------

@login_required_custom
@csrf_exempt
def share_family_member(request, id):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            return render(request, 'share_family_member.html', {'error': 'Email required.'})

        response = api_client.share_family_member(id, {'email': email})

        if response:
            return redirect('family_member_list')
        else:
            return render(request, 'share_family_member.html', {'error': 'User not found or error.'})

    else:
        return render(request, 'share_family_member.html')

@login_required_custom
@csrf_exempt
def edit_family_member(request, id):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        # 1) Construir data dict para texto, relaciones y eliminar imágenes
        data = request.POST.dict()
        if 'gender' not in data:
            data['gender'] = request.POST.get('gender', '')

        data['related_deceased']      = request.POST.getlist('related_deceased[]')
        data['relationship_type']     = request.POST.getlist('relationship_type[]')
        data['deleted_relation_ids']  = request.POST.getlist('deleted_relation_ids[]')
        data['delete_image_ids']      = request.POST.getlist('delete_image_ids[]')
        data['existing_image_id']     = request.POST.getlist('existing_image_id[]')
        data['existing_video_id']     = request.POST.getlist('existing_video_id[]')
        data['delete_video_ids']      = request.POST.getlist('delete_video_ids[]')

        # 2) Llamar a API para actualizar fallecido (texto, relaciones, imágenes)
        response = api_client.edit_family_member(id, data)

        if response and response.get("id_deceased"):
            # 3) Ahora procesar los archivos de vídeo SI llegaron
            #    En JavaScript normalmente enviarías FormData con archivos
            #    Pero, como aquí estamos en la vista de Django, tomamos request.FILES
            for idx, video_file in enumerate(request.FILES.getlist('videos')):
                event_title = request.POST.get(f'video_event_{idx}', '')
                description = request.POST.get(f'video_desc_{idx}', '')

                files = { 'video_file': video_file }
                payload = {
                    'id_deceased': id,
                    'event_title': event_title,
                    'description': description,
                }
                api_client.upload_video(payload, files)

            return redirect('family_member_list')

        else:
            error_msg = response.get('detail', 'Error editing family member.')
            return render(request, 'edit_family_member.html', {'error': error_msg})

    else:
        # GET: tal como indicamos, llamar a endpoints filtrados
        miembro    = api_client.get_deceased(id)
        relaciones = api_client.get_relations_by_deceased(id)
        imagenes   = api_client.get_images_by_deceased(id)
        videos     = api_client.get_videos_by_deceased(id)

        return render(request, 'edit_family_member.html', {
            'miembro':    miembro,
            'relaciones': relaciones,
            'imagenes':   imagenes,
            'videos':     videos,
        })



@login_required_custom
@csrf_exempt
def delete_family_member(request, id):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        success = api_client.delete_family_member(id)
        if success:
            return redirect('family_member_list')
        else:
            return render(request, 'delete_family_member.html', {'error': 'Error deleting.'})
    else:
        miembro = api_client.get_deceased(id)
        return render(request, 'delete_family_member.html', {'miembro': miembro})

@login_required_custom
@csrf_exempt
def request_access(request, id_deceased):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        resp = api_client.request_access(id_deceased)
        return redirect('family_member_list')
    else:
        return redirect('family_member_list')


@login_required_custom
@csrf_exempt
def approve_request(request, request_id, action):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        resp = api_client.approve_request(request_id, action)
        return redirect('family_member_list')
    else:
        return redirect('family_member_list')


@login_required_custom
def notifications(request):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    notifs = api_client.get_notifications()
    return render(request, 'notifications.html', {'notifications': notifs})


@login_required_custom
@csrf_exempt
def mark_notification_read(request, notification_id):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        api_client.mark_notification_read(notification_id)
        return redirect('family_member_list')
    else:
        return redirect('family_member_list')


@login_required_custom
@csrf_exempt
def handle_notification_action(request, notification_id, action):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        api_client.handle_notification_action(notification_id, action)
        return redirect('family_member_list')
    else:
        return redirect('family_member_list')


@login_required_custom
def ajax_search_deceased(request):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return JsonResponse({'results': []})

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})

    response = api_client.search_deceased(query)
    return JsonResponse(response)