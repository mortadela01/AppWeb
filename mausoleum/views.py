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

# @login_required_custom
# # === AppServer: views.py ===

# class EditFamilyMemberView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
#     parser_classes = [MultiPartParser, FormParser, JSONParser]

#     @transaction.atomic
#     def put(self, request, id):
#         miembro = get_object_or_404(Deceased, id_deceased=id)
#         user = request.user

#         # 2) Verificar permiso en TBL_USER_DECEASED
#         with connection.cursor() as cursor:
#             cursor.execute("""
#                 SELECT has_permission 
#                 FROM TBL_USER_DECEASED
#                 WHERE id_user = %s AND id_deceased = %s
#             """, [user.id_user, id])
#             if not cursor.fetchone():
#                 return Response({"detail": "No permission to edit this deceased."},
#                                 status=status.HTTP_403_FORBIDDEN)

#         # 3) Actualizar campos principales con el serializer
#         serializer = DeceasedSerializer(miembro, data=request.data, partial=True)
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#         serializer.save()

#         # 4) Manejo de relaciones en TBL_RELATION
#         if hasattr(request.data, 'getlist'):
#             related_ids = request.data.getlist('related_deceased[]')
#             relationship_types = request.data.getlist('relationship_type[]')
#             deleted_relation_ids = request.data.getlist('deleted_relation_ids[]')
#         else:
#             related_ids = request.data.get('related_deceased', [])
#             relationship_types = request.data.get('relationship_type', [])
#             deleted_relation_ids = request.data.get('deleted_relation_ids', [])

#         with connection.cursor() as cursor:
#             for del_id in deleted_relation_ids:
#                 cursor.execute("""
#                     DELETE FROM TBL_RELATION
#                     WHERE id_deceased = %s AND id_parent = %s
#                 """, [id, del_id])

#             cursor.execute("SELECT id_parent FROM TBL_RELATION WHERE id_deceased = %s", [id])
#             existing_ids = set(row[0] for row in cursor.fetchall())
#             for rid, rtype in zip(related_ids, relationship_types):
#                 if rid and rtype and int(rid) not in existing_ids:
#                     cursor.execute("""
#                         INSERT INTO TBL_RELATION (id_deceased, id_parent, relationship)
#                         VALUES (%s, %s, %s)
#                     """, [id, int(rid), rtype])

#         # 5) Manejo de imágenes
#         if hasattr(request.data, 'getlist'):
#             delete_image_ids = request.data.getlist('delete_image_ids[]')
#         else:
#             delete_image_ids = request.data.get('delete_image_ids', [])

#         existing_image_ids = (
#             request.data.get('existing_image_id')
#             or request.data.get('existing_image_id[]')
#             or []
#         )

#         with connection.cursor() as cursor:
#             # 5.1) Eliminar imágenes marcadas
#             for del_id in delete_image_ids:
#                 cursor.execute("DELETE FROM TBL_DECEASED_IMAGE WHERE id_metadata = %s", [del_id])
#                 cursor.execute("DELETE FROM TBL_IMAGE WHERE id_image = %s", [del_id])

#             # 5.2) Actualizar imágenes existentes
#             for idx, img_id in enumerate(existing_image_ids):
#                 events = request.data.get('existing_image_event') or request.data.get('existing_image_event[]') or []
#                 descs  = request.data.get('existing_image_desc')  or request.data.get('existing_image_desc[]')  or []
#                 event = events[idx] if idx < len(events) else ''
#                 desc  = descs[idx]  if idx < len(descs)  else ''
#                 cursor.execute("""
#                     UPDATE TBL_IMAGE
#                     SET event_title = %s, description = %s
#                     WHERE id_image = %s
#                 """, [event, desc, img_id])

#             # 5.3) Guardar nuevas imágenes
#             fs_imagenes = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'images'))
#             for idx, image_file in enumerate(request.FILES.getlist('images')):
#                 filename = fs_imagenes.save(image_file.name, image_file)
#                 uploaded_url = fs_imagenes.url(filename)
#                 event = request.data.get(f'image_event_{idx}', '')
#                 desc  = request.data.get(f'image_desc_{idx}', '')

#                 cursor.execute("INSERT INTO TBL_IMAGE_METADATA (date_created, coordinates) VALUES (%s, %s)",
#                                [datetime.now(), ""])
#                 metadata_id = cursor.lastrowid

#                 cursor.execute("INSERT INTO TBL_DECEASED_IMAGE (id_deceased, id_metadata, image_link) VALUES (%s, %s, %s)",
#                                [id, metadata_id, uploaded_url])
#                 cursor.execute("INSERT INTO TBL_IMAGE (id_image, image_link, event_title, description) VALUES (%s, %s, %s, %s)",
#                                [metadata_id, uploaded_url, event, desc])

#         # 6) Manejo de vídeos
#         if hasattr(request.data, 'getlist'):
#             delete_video_ids = request.data.getlist('delete_video_ids[]')
#         else:
#             delete_video_ids = request.data.get('delete_video_ids', [])

#         existing_video_ids = (
#             request.data.get('existing_video_id')
#             or request.data.get('existing_video_id[]')
#             or []
#         )

#         with connection.cursor() as cursor:
#             # 6.1) Eliminar vídeos marcados
#             for del_id in delete_video_ids:
#                 cursor.execute("DELETE FROM TBL_DECEASED_VIDEO WHERE id_metadata = %s", [del_id])
#                 cursor.execute("DELETE FROM TBL_VIDEO WHERE id_video = %s", [del_id])

#             # 6.2) Actualizar vídeos existentes
#             for idx, vid_id in enumerate(existing_video_ids):
#                 events = request.data.get('existing_video_event') or request.data.get('existing_video_event[]') or []
#                 descs  = request.data.get('existing_video_desc')  or request.data.get('existing_video_desc[]')  or []
#                 event = events[idx] if idx < len(events) else ''
#                 desc  = descs[idx]  if idx < len(descs) else ''
#                 cursor.execute("""
#                     UPDATE TBL_VIDEO
#                     SET event_title = %s, description = %s
#                     WHERE id_video = %s
#                 """, [event, desc, vid_id])

#             # 6.3) Guardar nuevos vídeos
#             fs_videos = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'videos'))
#             for idx, video_file in enumerate(request.FILES.getlist('videos')):
#                 filename = fs_videos.save(video_file.name, video_file)
#                 uploaded_url = fs_videos.url(filename)
#                 event = request.data.get(f'video_event_{idx}', '')
#                 desc  = request.data.get(f'video_desc_{idx}', '')

#                 cursor.execute("INSERT INTO TBL_VIDEO_METADATA (date_created, coordinates) VALUES (%s, %s)",
#                                [datetime.now(), ""])
#                 metadata_id = cursor.lastrowid

#                 cursor.execute("INSERT INTO TBL_DECEASED_VIDEO (id_deceased, id_metadata, video_link) VALUES (%s, %s, %s)",
#                                [id, metadata_id, uploaded_url])
#                 cursor.execute("INSERT INTO TBL_VIDEO (id_video, video_link, event_title, description) VALUES (%s, %s, %s, %s)",
#                                [metadata_id, uploaded_url, event, desc])

#         return Response(serializer.data, status=status.HTTP_200_OK)


# mausoleum/views.py  (AppWeb)
@login_required_custom
@csrf_exempt
def edit_family_member(request, id):
    user_session = request.session.get('user')
    if not user_session or 'access_token' not in user_session:
        return redirect('auth0_login')

    token = user_session['access_token']
    api_client = APIClient(access_token=token)

    if request.method == 'POST':
        raw = request.POST
        data = {}

        # Campos principales
        if raw.get('name', '').strip():
            data['name'] = raw.get('name').strip()
        if raw.get('date_birth', '').strip():
            data['date_birth'] = raw.get('date_birth').strip()
        if raw.get('date_death', '').strip():
            data['date_death'] = raw.get('date_death').strip()
        if raw.get('description', '').strip():
            data['description'] = raw.get('description').strip()
        if raw.get('burial_place', '').strip():
            data['burial_place'] = raw.get('burial_place').strip()
        if raw.get('visualization_state') == 'on':
            data['visualization_state'] = True
        if raw.get('visualization_code', '').strip():
            data['visualization_code'] = raw.get('visualization_code').strip()

        # Relaciones
        related_ids = raw.getlist('related_deceased[]')
        if related_ids:
            data['related_deceased'] = related_ids
            data['relationship_type'] = raw.getlist('relationship_type[]')
            data['deleted_relation_ids'] = raw.getlist('deleted_relation_ids[]')

        # Imágenes existentes
        exist_img_ids = raw.getlist('existing_image_id[]')
        if exist_img_ids:
            data['existing_image_id'] = exist_img_ids
            data['existing_image_event'] = [raw.get(f'existing_image_event_{i}', '') for i in range(len(exist_img_ids))]
            data['existing_image_desc'] = [raw.get(f'existing_image_desc_{i}', '') for i in range(len(exist_img_ids))]
            data['delete_image_ids'] = raw.getlist('delete_image_ids[]')

        # Vídeos existentes
        exist_vid_ids = raw.getlist('existing_video_id[]')
        if exist_vid_ids:
            data['existing_video_id'] = exist_vid_ids
            data['existing_video_event'] = [raw.get(f'existing_video_event_{i}', '') for i in range(len(exist_vid_ids))]
            data['existing_video_desc'] = [raw.get(f'existing_video_desc_{i}', '') for i in range(len(exist_vid_ids))]
            data['delete_video_ids'] = raw.getlist('delete_video_ids[]')

        # DEBUG
        # print("DEBUG → AppWeb: payload a enviar:", data)

        # 1) Actualizar objeto fallecido
        response = api_client.edit_family_member(id, data)

        if response and response.get("id_deceased"):
            # 2) Eliminar imágenes
            for img_id in raw.getlist('delete_image_ids[]'):
                api_client.delete_image(img_id)

            # 3) Actualizar imágenes existentes
            for idx, img_id in enumerate(raw.getlist('existing_image_id[]')):
                event_title = raw.get(f'existing_image_event_{idx}', '')
                description = raw.get(f'existing_image_desc_{idx}', '')
                if event_title or description:
                    payload = {'event_title': event_title, 'description': description}
                    api_client.update_image(img_id, payload)

            # 4) Subir nuevas imágenes
            for idx, image_file in enumerate(request.FILES.getlist('images')):
                event_title = raw.get(f'image_event_{idx}', '')
                description = raw.get(f'image_desc_{idx}', '')
                files = {'image_file': image_file}
                payload = {'event_title': event_title, 'description': description, 'id_deceased': id}
                api_client.upload_image(payload, files)

            # 5) Eliminar vídeos
            for vid_id in raw.getlist('delete_video_ids[]'):
                api_client.delete_video(vid_id)

            # 6) Actualizar vídeos existentes
            for idx, vid_id in enumerate(raw.getlist('existing_video_id[]')):
                event_title = raw.get(f'existing_video_event_{idx}', '')
                description = raw.get(f'existing_video_desc_{idx}', '')
                if event_title or description:
                    payload = {'event_title': event_title, 'description': description}
                    api_client.update_video(vid_id, payload)

            # 7) Subir nuevos vídeos
            for idx, video_file in enumerate(request.FILES.getlist('videos')):
                event_title = raw.get(f'video_event_{idx}', '')
                description = raw.get(f'video_desc_{idx}', '')
                files = {'video_file': video_file}
                payload = {'event_title': event_title, 'description': description, 'id_deceased': id}
                api_client.upload_video(payload, files)

            return redirect('family_member_list')
        else:
            error_msg = response.get('detail', 'Error editing family member.') if response else 'Sin respuesta del servidor.'
            return render(request, 'edit_family_member.html', {'error': error_msg})

    else:
        # GET
        miembro = api_client.get_deceased(id)
        relaciones = api_client.get_relations_by_deceased(id)
        imagenes = api_client.get_images_by_deceased(id)
        videos = api_client.get_videos_by_deceased(id)

        # print(imagenes)
        # print(videos)

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