import os
from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from .models import User, Deceased
from .forms import DeceasedForm, ShareDeceasedForm
from .forms import ImageForm, VideoForm
from .models import Image, Video
from .decorators import login_required_auth0
from django.utils import timezone
from django.conf import settings
import requests
from urllib.parse import urlencode

# -------------------- FUNCIONES DE AUTENTICACION --------------------

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

    # Guardar en la sesión
    request.session['user'] = {
        'email': email,
        'name': name,
        'picture': user_info.get('picture')
    }

    # Buscar por email primero
    usuario = User.objects.filter(email=email).first()
    if not usuario:
        usuario = User(
            name=name,
            email=email,
            password=sub
        )
        usuario.save()  # El id_user se asigna automático en la DB

    return redirect('dashboard')

def auth0_logout(request):
    request.session.flush()
    return redirect(f"https://{settings.AUTH0_DOMAIN}/v2/logout?" + urlencode({
        'client_id': settings.AUTH0_CLIENT_ID,
        'returnTo': 'http://localhost:8000'
    }))

# -------------------- FUNCIONALIDADES DE MEMORIAS --------------------

@login_required_auth0
def dashboard(request):
    user = request.session.get('user')
    return render(request, 'dashboard.html', {'user': user})

import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone
from django.db import connection
from django.shortcuts import render, redirect
from .forms import DeceasedForm
from .models import User, Deceased

@login_required_auth0
def add_family_member(request):
    if request.method == 'POST':
        form = DeceasedForm(request.POST)
        if form.is_valid():
            new_deceased = form.save()

            # === SOLUCIÓN: insertar relación User-Deceased aquí ===
            user_session = request.session.get('user')
            if user_session:
                user = User.objects.filter(email=user_session.get('email')).first()
                if user:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, permits)
                            VALUES (%s, %s, %s, %s)
                        """, [user.id_user, new_deceased.id_deceased, timezone.now(), 1])
            # ===============================================

            # Luego continúa normalmente con las imágenes y videos
            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'images'))
            fs_video = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'videos'))

            # -------------------------
            # Ahora sí puedes usar fs y fs_video más adelante
            # -------------------------

            images = request.FILES.getlist('images')
            for idx, image_file in enumerate(images):
                filename = fs.save(image_file.name, image_file)
                uploaded_file_url = fs.url(filename)

                event_title = request.POST.get(f'image_event_{idx}', '')
                description = request.POST.get(f'image_desc_{idx}', '')

                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO TBL_METADATA_IMAGE (date_created, coordenates)
                        VALUES (%s, %s)
                    """, [timezone.now(), ""])
                    metadata_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO TBL_DECEASED_IMAGE (id_deceased, id_metadata, link_image)
                        VALUES (%s, %s, %s)
                    """, [new_deceased.id_deceased, metadata_id, uploaded_file_url])

                    cursor.execute("""
                        INSERT INTO TBL_IMAGE (id_image, link_image, event_title, description)
                        VALUES (%s, %s, %s, %s)
                    """, [metadata_id, uploaded_file_url, event_title, description])

            video_files = request.FILES.getlist('videos')
            for idx, video_file in enumerate(video_files):
                filename = fs_video.save(video_file.name, video_file)
                uploaded_video_url = fs_video.url(filename)

                event_title = request.POST.get(f'video_event_{idx}', '')
                description = request.POST.get(f'video_desc_{idx}', '')

                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO TBL_METADATA_VIDEO (date_created, coordenates)
                        VALUES (%s, %s)
                    """, [timezone.now(), ""])
                    metadata_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO TBL_DECEASED_VIDEO (id_deceased, id_metadata, link_video)
                        VALUES (%s, %s, %s)
                    """, [new_deceased.id_deceased, metadata_id, uploaded_video_url])

                    cursor.execute("""
                        INSERT INTO TBL_VIDEO (id_video, link_video, event_title, description)
                        VALUES (%s, %s, %s, %s)
                    """, [metadata_id, uploaded_video_url, event_title, description])

            return redirect('family_member_list')

    else:
        form = DeceasedForm()

    return render(request, 'add_family_member.html', {'form': form})

@login_required_auth0
def family_member_list(request):
    user_session = request.session.get('user')
    miembros = []
    permisos = {}

    if user_session:
        user = User.objects.filter(email=user_session.get('email')).first()
        if user:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT d.*, ud.permits FROM TBL_DECEASED d
                    INNER JOIN TBL_USER_DECEASED ud ON d.id_deceased = ud.id_deceased
                    WHERE ud.id_user = %s
                """, [user.id_user])
                rows = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
                for row in rows:
                    miembro = dict(zip(columns, row))
                    permisos[miembro['id_deceased']] = miembro['permits']
                    miembros.append(miembro)

    return render(request, 'family_member_list.html', {'miembros': miembros, 'permisos': permisos})

@login_required_auth0
def share_family_member(request, id):
    form = ShareDeceasedForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data['email']
        shared_user = User.objects.filter(email=email).first()
        if shared_user:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT IGNORE INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, permits)
                    VALUES (%s, %s, %s, %s)
                """, [shared_user.id_user, id, timezone.now(), 0])
            return redirect('family_member_list')
        else:
            form.add_error('email', 'User with this email does not exist.')

    return render(request, 'share_family_member.html', {'form': form})

@login_required_auth0
def edit_family_member(request, id):
    miembro = get_object_or_404(Deceased, id_deceased=id)
    form = DeceasedForm(request.POST or None, instance=miembro)
    if form.is_valid():
        form.save()
        return redirect('family_member_list')
    return render(request, 'edit_family_member.html', {'form': form, 'miembro': miembro})

@login_required_auth0
def delete_family_member(request, id):
    miembro = get_object_or_404(Deceased, id_deceased=id)
    if request.method == 'POST':
        miembro.delete()
        return redirect('family_member_list')
    return render(request, 'delete_family_member.html', {'miembro': miembro})

