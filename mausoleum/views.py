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
from django.core.mail import send_mail
import re 


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

            # Guardar relaciones con otros fallecidos si se envían
            related_ids = request.POST.getlist('related_deceased[]')
            relationship_types = request.POST.getlist('relationship_type[]')

            for related_id, rel_type in zip(related_ids, relationship_types):
                if related_id and rel_type:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO TBL_RELATION (id_deceased, id_parent, relationship)
                            VALUES (%s, %s, %s)
                        """, [new_deceased.id_deceased, int(related_id), rel_type])


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

        all_deceased = Deceased.objects.all()
    return render(request, 'add_family_member.html', {'form': form, 'all_deceased': all_deceased})

import re  # Asegúrate de tener este import al inicio del archivo

@login_required_auth0
def family_member_list(request):
    user_session = request.session.get('user')
    miembros = []
    permisos = []
    otros_deceased = []
    notifications = []
    unread_count = 0

    if user_session:
        user = User.objects.filter(email=user_session.get('email')).first()
        if user:
            with connection.cursor() as cursor:
                # Familiares a los que sí tiene acceso
                cursor.execute("""
                    SELECT d.*, ud.permits FROM TBL_DECEASED d
                    INNER JOIN TBL_USER_DECEASED ud ON d.id_deceased = ud.id_deceased
                    WHERE ud.id_user = %s
                """, [user.id_user])
                rows = cursor.fetchall()
                columns = [col[0] for col in cursor.description]
                for row in rows:
                    miembro = dict(zip(columns, row))
                    permisos.append(miembro['permits'])
                    miembros.append(miembro)

                # Familiares a los que NO tiene acceso
                cursor.execute("""
                    SELECT * FROM TBL_DECEASED
                    WHERE id_deceased NOT IN (
                        SELECT id_deceased FROM TBL_USER_DECEASED WHERE id_user = %s
                    )
                """, [user.id_user])
                disponibles = cursor.fetchall()
                disponibles_columns = [col[0] for col in cursor.description]
                otros_deceased = [dict(zip(disponibles_columns, row)) for row in disponibles]

                # Notificaciones como dicts
                cursor.execute("""
                    SELECT * FROM TBL_NOTIFICATION
                    WHERE id_user = %s ORDER BY date_created DESC
                """, [user.id_user])
                notifications_rows = cursor.fetchall()
                notifications_columns = [col[0] for col in cursor.description]
                notifications = []
                for row in notifications_rows:
                    notif = dict(zip(notifications_columns, row))
                    match = re.search(r"Request #(\d+)", notif["message"])
                    if match:
                        notif["request_id"] = match.group(1)
                    notifications.append(notif)

                # Contador de no leídas
                cursor.execute("""
                    SELECT COUNT(*) FROM TBL_NOTIFICATION
                    WHERE id_user = %s AND is_read = 0
                """, [user.id_user])
                unread_count = cursor.fetchone()[0]

    return render(request, 'family_member_list.html', {
        'miembros': miembros,
        'permisos': permisos,
        'otros_deceased': otros_deceased,
        'notifications': notifications,
        'unread_count': unread_count
    })



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


# -------------------- FUNCIONALIDADES DE ACCESO --------------------

    
@login_required_auth0
def request_access(request, id_deceased):
    import re
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()

    with connection.cursor() as cursor:
        # Obtener dueño del fallecido
        cursor.execute("""
            SELECT id_user FROM TBL_USER_DECEASED WHERE id_deceased = %s AND permits = 1 LIMIT 1
        """, [id_deceased])
        creator_id = cursor.fetchone()[0]

        # Insertar solicitud (solo una vez)
        cursor.execute("""
            INSERT INTO TBL_ACCESS_REQUEST (id_user_requester, id_deceased, date_requested)
            VALUES (%s, %s, %s)
        """, [user.id_user, id_deceased, timezone.now()])
        request_id = cursor.lastrowid  # obtener el ID de la solicitud

        # Insertar notificación con ID embebido
        cursor.execute("""
            INSERT INTO TBL_NOTIFICATION (id_user, message, date_created)
            VALUES (%s, %s, %s)
        """, [
            creator_id,
            f"{user.name} has requested access to a family memory. Request #{request_id}",
            timezone.now()
        ])

    return redirect('family_member_list')

@login_required_auth0
def request_access(request, id_deceased):
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()

    with connection.cursor() as cursor:
        # Verificar si ya existe una solicitud pendiente
        cursor.execute("""
            SELECT COUNT(*) FROM TBL_ACCESS_REQUEST
            WHERE id_user_requester = %s AND id_deceased = %s AND status = 'pending'
        """, [user.id_user, id_deceased])
        if cursor.fetchone()[0] > 0:
            # Ya existe una solicitud pendiente, no duplicar
            return redirect('family_member_list')

        # Obtener dueño del fallecido
        cursor.execute("""
            SELECT id_user FROM TBL_USER_DECEASED 
            WHERE id_deceased = %s AND permits = 1 
            LIMIT 1
        """, [id_deceased])
        creator_id = cursor.fetchone()[0]

        # Insertar solicitud
        cursor.execute("""
            INSERT INTO TBL_ACCESS_REQUEST (id_user_requester, id_deceased, date_requested)
            VALUES (%s, %s, %s)
        """, [user.id_user, id_deceased, timezone.now()])
        request_id = cursor.lastrowid

        # Insertar notificación con ID embebido
        cursor.execute("""
            INSERT INTO TBL_NOTIFICATION (id_user, message, date_created)
            VALUES (%s, %s, %s)
        """, [
            creator_id,
            f"{user.name} has requested access to a family memory. Request #{request_id}",
            timezone.now()
        ])

    return redirect('family_member_list')

@login_required_auth0
def approve_request(request, request_id, action):
    with connection.cursor() as cursor:
        # Obtener quién pidió y sobre qué memoria
        cursor.execute("""
            SELECT id_user_requester, id_deceased 
            FROM TBL_ACCESS_REQUEST 
            WHERE id_request = %s
        """, [request_id])
        result = cursor.fetchone()

        if result:
            requester_id, deceased_id = result

            # Actualizar estado de la solicitud
            cursor.execute("""
                UPDATE TBL_ACCESS_REQUEST
                SET status = %s, date_resolved = %s
                WHERE id_request = %s
            """, [action, timezone.now(), request_id])

            # Si fue aprobado, dar acceso
            if action == 'approved':
                cursor.execute("""
                    INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, permits)
                    VALUES (%s, %s, %s, %s)
                """, [requester_id, deceased_id, timezone.now(), 1])

                message = f"✅ Your access request to memory ID {deceased_id} was approved."
            else:
                message = f"❌ Your request to access memory ID {deceased_id} was rejected."

            # Insertar notificación
            cursor.execute("""
                INSERT INTO TBL_NOTIFICATION (id_user, message, date_created)
                VALUES (%s, %s, %s)
            """, [requester_id, message, timezone.now()])

    return redirect('view_requests')


@login_required_auth0
def notifications(request):
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()
    notifications = []

    if user:
        with connection.cursor() as cursor:
            # Marcar como leídas
            cursor.execute("""
                UPDATE TBL_NOTIFICATION
                SET is_read = 1
                WHERE id_user = %s AND is_read = 0
            """, [user.id_user])

            # Recuperar todas las notificaciones
            cursor.execute("""
                SELECT * FROM TBL_NOTIFICATION
                WHERE id_user = %s
                ORDER BY date_created DESC
            """, [user.id_user])

            notifications = cursor.fetchall()

    return render(request, 'notifications.html', {
        'notifications': notifications
    })


def send_email_to_creator(to_email, subject, message):
    send_mail(
        subject,
        message,
        'noreply@mausoleum.com',
        [to_email],
        fail_silently=False,
    )

@login_required_auth0
def mark_notification_read(request, notification_id):
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()

    if user:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE TBL_NOTIFICATION
                SET is_read = 1
                WHERE id_notification = %s AND id_user = %s
            """, [notification_id, user.id_user])

    return redirect('family_member_list')



