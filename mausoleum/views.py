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
        # Copiar datos del formulario
        data = request.POST.dict()
        # Para listas, extraerlas directamente desde POST
        data['related_deceased'] = request.POST.getlist('related_deceased[]')
        data['relationship_type'] = request.POST.getlist('relationship_type[]')
        # Agrega campos adicionales que necesites

        # Llamar API para crear fallecido
        response = api_client.add_family_member(data)

        if response:
            # Aquí falta manejar subida de multimedia (imagenes/videos) por separado
            # Puedes redirigir a lista o a un mensaje éxito
            return redirect('family_member_list')
        else:
            # Manejo de error
            return render(request, 'add_family_member.html', {'error': 'Error creating family member.'})

    else:
        # GET: obtener lista de fallecidos para autocompletar
        deceased_list = api_client.list_deceased()

        return render(request, 'add_family_member.html', {
            'all_deceased': deceased_list,
        })


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

    return render(request, 'family_member_list.html', {
        'miembros': miembros,
        'permisos': permisos,
        'otros_deceased': otros_deceased,
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
        data = request.POST.dict()
        data['related_deceased'] = request.POST.getlist('related_deceased[]')
        data['relationship_type'] = request.POST.getlist('relationship_type[]')
        data['deleted_relation_ids'] = request.POST.getlist('deleted_relation_ids[]')

        response = api_client.edit_family_member(id, data)
        if response:
            # Manejar multimedia en otro endpoint
            return redirect('family_member_list')
        else:
            return render(request, 'edit_family_member.html', {'error': 'Error editing family member.'})

    else:
        # GET para obtener datos
        miembro = api_client.get_deceased(id)

        # Obtener relaciones, imágenes y videos por separado (llamadas API específicas)
        relaciones = api_client.list_relations()  # Filtrar client-side por fallecido
        imagenes = api_client.list_images()       # Filtrar client-side
        videos = api_client.list_videos()         # Filtrar client-side

        # Para simplicidad puedes hacer llamadas específicas para ese fallecido si los endpoints existen

        return render(request, 'edit_family_member.html', {
            'miembro': miembro,
            'relaciones': relaciones,
            'imagenes': imagenes,
            'videos': videos,
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


# -------------------- REQUEST ACCESS & NOTIFICATIONS --------------------

# @login_required_custom_auth0
# def request_access(request, id_deceased):
#     user_session = request.session.get('user')
#     user = User.objects.filter(email=user_session['email']).first()
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT COUNT(*) FROM TBL_REQUEST
#             WHERE id_issuer = %s AND id_deceased = %s AND request_status = 'pending'
#         """, [user.id_user, id_deceased])
#         if cursor.fetchone()[0] > 0:
#             return redirect('family_member_list')

#         cursor.execute("""
#             SELECT id_user FROM TBL_USER_DECEASED
#             WHERE id_deceased = %s AND has_permission = 1 LIMIT 1
#         """, [id_deceased])
#         creator_id = cursor.fetchone()[0]

#         cursor.execute("""
#             INSERT INTO TBL_REQUEST (id_issuer, id_receiver, id_deceased, creation_date, request_type, request_status)
#             VALUES (%s, %s, %s, %s, %s, %s)
#         """, [user.id_user, creator_id, id_deceased, timezone.now(), 'view', 'pending'])
#         request_id = cursor.lastrowid

#         cursor.execute("""
#             INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, creation_date)
#             VALUES (%s, %s, %s, %s)
#         """, [user.id_user, creator_id, f"{user.name} has requested access. Request #{request_id}", timezone.now()])
#     return redirect('family_member_list')

# @login_required_custom_auth0
# def approve_request(request, request_id, action):
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT id_issuer, id_deceased FROM TBL_REQUEST WHERE id_request = %s
#         """, [request_id])
#         requester_id, deceased_id = cursor.fetchone()

#         cursor.execute("""
#             UPDATE TBL_REQUEST SET request_status = %s WHERE id_request = %s
#         """, [action, request_id])

#         if action == 'approved':
#             cursor.execute("""
#                 INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
#                 VALUES (%s, %s, %s, %s)
#             """, [requester_id, deceased_id, timezone.now(), 1])
#             message = f"✅ Your request to access memory ID {deceased_id} was approved."
#         else:
#             message = f"❌ Your request to access memory ID {deceased_id} was rejected."

#         cursor.execute("""
#             INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, creation_date)
#             VALUES (%s, %s, %s, %s)
#         """, [0, requester_id, message, timezone.now()])
#     return redirect('view_requests')

# @login_required_custom_auth0
# def notifications(request):
#     user_session = request.session.get('user')
#     user = User.objects.filter(email=user_session['email']).first()
#     notifications = []
#     if user:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 UPDATE TBL_NOTIFICATION SET is_read = 1 WHERE id_receiver = %s
#             """, [user.id_user])
#             cursor.execute("""
#                 SELECT * FROM TBL_NOTIFICATION WHERE id_receiver = %s ORDER BY creation_date DESC
#             """, [user.id_user])
#             notifications = cursor.fetchall()
#     return render(request, 'notifications.html', {'notifications': notifications})

# @login_required_custom_auth0
# def mark_notification_read(request, notification_id):
#     user_session = request.session.get('user')
#     user = User.objects.filter(email=user_session['email']).first()
#     if user:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 UPDATE TBL_NOTIFICATION SET is_read = 1 WHERE id_notification = %s AND id_receiver = %s
#             """, [notification_id, user.id_user])
#     return redirect('family_member_list')

# @login_required_custom_auth0
# def handle_notification_action(request, notification_id, action):
#     user_session = request.session.get('user')
#     current_user = User.objects.filter(email=user_session['email']).first()

#     if request.method == 'POST' and current_user:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT id_sender, message FROM TBL_NOTIFICATION
#                 WHERE id_notification = %s AND id_receiver = %s
#             """, [notification_id, current_user.id_user])
#             notif = cursor.fetchone()

#             if notif:
#                 sender_id, message = notif
#                 match = re.search(r"memory ID (\d+)", message)

#                 if match:
#                     id_deceased = int(match.group(1))

#                     if action == 'accept':
#                         cursor.execute("""
#                             INSERT IGNORE INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
#                             VALUES (%s, %s, %s, %s)
#                         """, [current_user.id_user, id_deceased, timezone.now(), 0])
#                     # Ya sea accept, decline o read: marcar como leída
#                 cursor.execute("""
#                     UPDATE TBL_NOTIFICATION SET is_read = 1 WHERE id_notification = %s
#                 """, [notification_id])
#                 connection.commit()  # <-- AÑADE ESTA LÍNEA

#     return redirect('family_member_list')


# @login_required_custom_auth0
# def approve_request(request, request_id, action):
#     user_session = request.session.get('user')
#     approver = User.objects.filter(email=user_session['email']).first()

#     with connection.cursor() as cursor:
#         cursor.execute("""
#             SELECT id_issuer, id_deceased FROM TBL_REQUEST WHERE id_request = %s
#         """, [request_id])
#         requester_id, deceased_id = cursor.fetchone()

#         cursor.execute("""
#             UPDATE TBL_REQUEST SET request_status = %s WHERE id_request = %s
#         """, [action, request_id])

#         if action == 'approved':
#             # Primero borramos si ya existe (prevención de duplicados)
#             cursor.execute("""
#                 DELETE FROM TBL_USER_DECEASED WHERE id_user = %s AND id_deceased = %s
#             """, [requester_id, deceased_id])

#             cursor.execute("""
#                 INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
#                 VALUES (%s, %s, %s, %s)
#             """, [requester_id, deceased_id, timezone.now(), 0])

#             message = f"✅ Your request to access memory ID {deceased_id} was approved."
#         else:
#             message = f"❌ Your request to access memory ID {deceased_id} was rejected."

#         cursor.execute("""
#             INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, creation_date, is_read)
#             VALUES (%s, %s, %s, %s, %s)
#         """, [approver.id_user, requester_id, message, timezone.now(), 0])

#     return redirect('family_member_list')


# @require_GET
# def ajax_search_deceased(request):
#     query = request.GET.get('q', '').strip()
#     results = []
#     if query:
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT id_deceased, name FROM TBL_DECEASED
#                 WHERE LOWER(name) LIKE %s
#                 LIMIT 10
#             """, [f"%{query.lower()}%"])
#             rows = cursor.fetchall()
#             for row in rows:
#                 results.append({
#                     'id': row[0],
#                     'name': row[1]
#                 })
#     return JsonResponse({'results': results})

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
        return redirect('view_requests')
    else:
        return redirect('view_requests')


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