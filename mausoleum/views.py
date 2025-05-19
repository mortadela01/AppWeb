import os
import re
import requests
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.db import connection
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.mail import send_mail
from .decorators import login_required_auth0
from .forms import DeceasedForm, ShareDeceasedForm, ImageForm, VideoForm
from .models import User, Deceased
from django.db import connection
from django.views.decorators.http import require_GET
from django.http import JsonResponse



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

    request.session['user'] = {
        'email': email,
        'name': name,
        'picture': user_info.get('picture')
    }

    usuario = User.objects.filter(email=email).first()
    if not usuario:
        usuario = User(name=name, email=email, password=sub)
        usuario.save()

    return redirect('dashboard')

def auth0_logout(request):
    request.session.flush()
    return redirect(f"https://{settings.AUTH0_DOMAIN}/v2/logout?" + urlencode({
        'client_id': settings.AUTH0_CLIENT_ID,
        'returnTo': 'http://localhost:8000'
    }))

# -------------------- DASHBOARD --------------------

@login_required_auth0
def dashboard(request):
    user_session = request.session.get('user')
    notifications = []
    unread_count = 0

    if user_session:
        user = User.objects.filter(email=user_session.get('email')).first()
        if user:
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM TBL_NOTIFICATION
                    WHERE id_receiver = %s ORDER BY creation_date DESC
                """, [user.id_user])
                columns = [col[0] for col in cursor.description]
                notifications = []
                for row in cursor.fetchall():
                    notif = dict(zip(columns, row))
                    match = re.search(r"Request #(\d+)", notif["message"])
                    if match:
                        notif["request_id"] = match.group(1)
                    notifications.append(notif)

                cursor.execute("""
                    SELECT COUNT(*) FROM TBL_NOTIFICATION
                    WHERE id_receiver = %s AND is_read = 0
                """, [user.id_user])
                unread_count = cursor.fetchone()[0]

    return render(request, 'dashboard.html', {
        'user': user_session,
        'notifications': notifications,
        'unread_count': unread_count,
    })


# -------------------- ADD FAMILY MEMBER --------------------

@login_required_auth0
def add_family_member(request):
    if request.method == 'POST':
        form = DeceasedForm(request.POST)
        if form.is_valid():
            new_deceased = form.save(commit=False)
            new_deceased.description = request.POST.get('biography', '')
            new_deceased.save()

            related_ids = request.POST.getlist('related_deceased[]')
            relationship_types = request.POST.getlist('relationship_type[]')

            for related_id, rel_type in zip(related_ids, relationship_types):
                if related_id and rel_type:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO TBL_RELATION (id_deceased, id_parent, relationship)
                            VALUES (%s, %s, %s)
                        """, [new_deceased.id_deceased, int(related_id), rel_type])

            user_session = request.session.get('user')
            if user_session:
                user = User.objects.filter(email=user_session.get('email')).first()
                if user:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
                            VALUES (%s, %s, %s, %s)
                        """, [user.id_user, new_deceased.id_deceased, timezone.now(), 1])

            fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'images'))
            fs_video = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'videos'))

            images = request.FILES.getlist('images')
            for idx, image_file in enumerate(images):
                filename = fs.save(image_file.name, image_file)
                uploaded_file_url = fs.url(filename)
                event_title = request.POST.get(f'image_event_{idx}', '')
                description = request.POST.get(f'image_desc_{idx}', '')

                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO TBL_IMAGE_METADATA (date_created, coordinates)
                        VALUES (%s, %s)
                    """, [timezone.now(), ""])
                    metadata_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO TBL_DECEASED_IMAGE (id_deceased, id_metadata, image_link)
                        VALUES (%s, %s, %s)
                    """, [new_deceased.id_deceased, metadata_id, uploaded_file_url])

                    cursor.execute("""
                        INSERT INTO TBL_IMAGE (id_image, image_link, event_title, description)
                        VALUES (%s, %s, %s, %s)
                    """, [metadata_id, uploaded_file_url, event_title, description])

            video_files = request.FILES.getlist('videos')
            connection.commit()
            for idx, video_file in enumerate(video_files):
                filename = fs_video.save(video_file.name, video_file)
                uploaded_video_url = fs_video.url(filename)
                event_title = request.POST.get(f'video_event_{idx}', '')
                description = request.POST.get(f'video_desc_{idx}', '')

                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO TBL_VIDEO_METADATA (date_created, coordinates)
                        VALUES (%s, %s)
                    """, [timezone.now(), ""])
                    metadata_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO TBL_DECEASED_VIDEO (id_deceased, id_metadata, video_link)
                        VALUES (%s, %s, %s)
                    """, [new_deceased.id_deceased, metadata_id, uploaded_video_url])

                    cursor.execute("""
                        INSERT INTO TBL_VIDEO (id_video, video_link, event_title, description)
                        VALUES (%s, %s, %s, %s)
                    """, [metadata_id, uploaded_video_url, event_title, description])

            return redirect('family_member_list')

    else:
        form = DeceasedForm()
        all_deceased = Deceased.objects.all()

        # Notificaciones
        user_session = request.session.get('user')
        notifications = []
        unread_count = 0

        if user_session:
            user = User.objects.filter(email=user_session.get('email')).first()
            if user:
                with connection.cursor() as cursor:
                    
                    cursor.execute("""
                        SELECT * FROM TBL_NOTIFICATION
                        WHERE id_receiver = %s ORDER BY creation_date DESC
                    """, [user.id_user])
                    columns = [col[0] for col in cursor.description]
                    notifications = []
                    for row in cursor.fetchall():
                        notif = dict(zip(columns, row))
                        match = re.search(r"Request #(\d+)", notif["message"])
                        if match:
                            notif["request_id"] = match.group(1)
                        notifications.append(notif)


                    cursor.execute("""
                        SELECT COUNT(*) FROM TBL_NOTIFICATION
                        WHERE id_receiver = %s AND is_read = 0
                    """, [user.id_user])
                    unread_count = cursor.fetchone()[0]

    return render(request, 'add_family_member.html', {
        'form': form,
        'all_deceased': all_deceased,
        'notifications': notifications,
        'unread_count': unread_count
    })


# -------------------- FAMILY MEMBER LIST --------------------

@login_required_auth0
def family_member_list(request):
    user_session = request.session.get('user')
    miembros, permisos, otros_deceased, notifications = [], [], [], []
    unread_count = 0

    if user_session:
        user = User.objects.filter(email=user_session.get('email')).first()
        if user:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT d.id_deceased, d.name, d.date_birth, d.date_death, d.burial_place, ud.has_permission 
                    FROM TBL_DECEASED d
                    INNER JOIN TBL_USER_DECEASED ud ON d.id_deceased = ud.id_deceased
                    WHERE ud.id_user = %s
                """, [user.id_user])
                for row in cursor.fetchall():
                    columns = [col[0] for col in cursor.description]
                    miembro = dict(zip(columns, row))
                    permisos.append(miembro['has_permission'])
                    miembros.append(miembro)

                cursor.execute("""
                    SELECT * FROM TBL_DECEASED
                    WHERE id_deceased NOT IN (
                        SELECT id_deceased FROM TBL_USER_DECEASED WHERE id_user = %s
                    )
                """, [user.id_user])
                otros_deceased = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

                cursor.execute("""
                    SELECT * FROM TBL_NOTIFICATION
                    WHERE id_receiver = %s ORDER BY creation_date DESC
                """, [user.id_user])
                for row in cursor.fetchall():
                    notif = dict(zip([col[0] for col in cursor.description], row))
                    match = re.search(r"Request #(\d+)", notif["message"])
                    if match:
                        notif["request_id"] = match.group(1)
                    notifications.append(notif)

                cursor.execute("""
                    SELECT COUNT(*) FROM TBL_NOTIFICATION
                    WHERE id_receiver = %s AND is_read = 0
                """, [user.id_user])
                unread_count = cursor.fetchone()[0]

    return render(request, 'family_member_list.html', {
        'miembros': miembros,
        'permisos': permisos,
        'otros_deceased': otros_deceased,
        'notifications': notifications,
        'unread_count': unread_count
    })


# -------------------- SHARE / EDIT / DELETE --------------------

@login_required_auth0
def share_family_member(request, id):
    form = ShareDeceasedForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data['email']
        shared_user = User.objects.filter(email=email).first()
        user_session = request.session.get('user')
        sender = User.objects.filter(email=user_session.get('email')).first()

        if shared_user and sender:
            with connection.cursor() as cursor:
                # Crear la notificación dirigida al usuario que va a recibir la memoria (usuario 2)
                cursor.execute("""
                    INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, is_read, creation_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, [
                    sender.id_user,  # Quien está compartiendo (usuario 1)
                    shared_user.id_user,  # Quien recibirá la notificación (usuario 2)
                    f"{sender.name} has shared memory ID {id} with you. Do you approve?",
                    0,
                    timezone.now()
                ])
            return redirect('family_member_list')
        else:
            form.add_error('email', 'User with this email does not exist.')

    return render(request, 'share_family_member.html', {'form': form})

@login_required_auth0
def edit_family_member(request, id):
    miembro = get_object_or_404(Deceased, id_deceased=id)
    user_session = request.session.get('user')
    current_user = User.objects.filter(email=user_session['email']).first()

    # Verificar permiso
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT has_permission FROM TBL_USER_DECEASED
            WHERE id_user = %s AND id_deceased = %s
        """, [current_user.id_user, id])
        perm = cursor.fetchone()
        if not perm:
            return redirect('family_member_list')

    if request.method == 'POST':
        form = DeceasedForm(request.POST, instance=miembro)
        if form.is_valid():
            form.save()

            related_ids = request.POST.getlist('related_deceased[]')
            relationship_types = request.POST.getlist('relationship_type[]')
            deleted_relation_ids = request.POST.getlist('deleted_relation_ids[]')

            with connection.cursor() as cursor:
                # Eliminar relaciones marcadas para borrar
                for del_id in deleted_relation_ids:
                    cursor.execute("""
                        DELETE FROM TBL_RELATION
                        WHERE id_deceased = %s AND id_parent = %s
                    """, [id, del_id])

                # Obtener relaciones existentes
                cursor.execute("SELECT id_parent FROM TBL_RELATION WHERE id_deceased = %s", [id])
                existing_ids = set(row[0] for row in cursor.fetchall())

                # Insertar relaciones nuevas si no están ya
                for related_id, rel_type in zip(related_ids, relationship_types):
                    if related_id and rel_type and int(related_id) not in existing_ids:
                        cursor.execute("""
                            INSERT INTO TBL_RELATION (id_deceased, id_parent, relationship)
                            VALUES (%s, %s, %s)
                        """, [id, int(related_id), rel_type])

                # Manejo imágenes
                delete_image_ids = request.POST.getlist('delete_image_ids[]')
                for del_id in delete_image_ids:
                    cursor.execute("DELETE FROM TBL_DECEASED_IMAGE WHERE id_metadata = %s", [del_id])
                    cursor.execute("DELETE FROM TBL_IMAGE WHERE id_image = %s", [del_id])

                existing_image_ids = request.POST.getlist('existing_image_id[]')
                for idx, img_id in enumerate(existing_image_ids):
                    event = request.POST.get(f'existing_image_event_{idx}', '')
                    desc = request.POST.get(f'existing_image_desc_{idx}', '')
                    cursor.execute("""
                        UPDATE TBL_IMAGE SET event_title=%s, description=%s WHERE id_image=%s
                    """, [event, desc, img_id])

                fs = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'images'))
                for idx, image_file in enumerate(request.FILES.getlist('images')):
                    filename = fs.save(image_file.name, image_file)
                    uploaded_file_url = fs.url(filename)
                    event = request.POST.get(f'image_event_{idx}', '')
                    desc = request.POST.get(f'image_desc_{idx}', '')

                    cursor.execute("INSERT INTO TBL_IMAGE_METADATA (date_created, coordinates) VALUES (%s, %s)",
                                   [timezone.now(), ""])
                    metadata_id = cursor.lastrowid

                    cursor.execute("INSERT INTO TBL_DECEASED_IMAGE (id_deceased, id_metadata, image_link) VALUES (%s, %s, %s)",
                                   [id, metadata_id, uploaded_file_url])
                    cursor.execute("INSERT INTO TBL_IMAGE (id_image, image_link, event_title, description) VALUES (%s, %s, %s, %s)",
                                   [metadata_id, uploaded_file_url, event, desc])

                # Manejo videos
                delete_video_ids = request.POST.getlist('delete_video_ids[]')
                for del_id in delete_video_ids:
                    cursor.execute("DELETE FROM TBL_DECEASED_VIDEO WHERE id_metadata = %s", [del_id])
                    cursor.execute("DELETE FROM TBL_VIDEO WHERE id_video = %s", [del_id])

                existing_video_ids = request.POST.getlist('existing_video_id[]')
                for idx, vid_id in enumerate(existing_video_ids):
                    event = request.POST.get(f'existing_video_event_{idx}', '')
                    desc = request.POST.get(f'existing_video_desc_{idx}', '')
                    cursor.execute("""
                        UPDATE TBL_VIDEO SET event_title=%s, description=%s WHERE id_video=%s
                    """, [event, desc, vid_id])

                fs_video = FileSystemStorage(location=os.path.join(settings.MEDIA_ROOT, 'uploads', 'videos'))
                for idx, video_file in enumerate(request.FILES.getlist('videos')):
                    filename = fs_video.save(video_file.name, video_file)
                    uploaded_video_url = fs_video.url(filename)
                    event = request.POST.get(f'video_event_{idx}', '')
                    desc = request.POST.get(f'video_desc_{idx}', '')

                    cursor.execute("INSERT INTO TBL_VIDEO_METADATA (date_created, coordinates) VALUES (%s, %s)",
                                   [timezone.now(), ""])
                    metadata_id = cursor.lastrowid

                    cursor.execute("INSERT INTO TBL_DECEASED_VIDEO (id_deceased, id_metadata, video_link) VALUES (%s, %s, %s)",
                                   [id, metadata_id, uploaded_file_url])
                    cursor.execute("INSERT INTO TBL_VIDEO (id_video, video_link, event_title, description) VALUES (%s, %s, %s, %s)",
                                   [metadata_id, uploaded_video_url, event, desc])

            return redirect('family_member_list')

    else:
        form = DeceasedForm(instance=miembro)

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT r.id_parent, r.relationship, d.name
                FROM TBL_RELATION r
                JOIN TBL_DECEASED d ON r.id_parent = d.id_deceased
                WHERE r.id_deceased = %s
            """, [id])
            relaciones = [{'id_parent': r[0], 'relationship': r[1], 'parent_name': r[2]} for r in cursor.fetchall()]

            cursor.execute("""
                SELECT im.id_metadata, im.image_link, i.event_title, i.description
                FROM TBL_DECEASED_IMAGE im
                JOIN TBL_IMAGE i ON im.id_metadata = i.id_image
                WHERE im.id_deceased = %s
            """, [id])
            imagenes = [dict(zip(['id_metadata', 'image_link', 'event_title', 'description'], r)) for r in cursor.fetchall()]

            cursor.execute("""
                SELECT vm.id_metadata, vm.video_link, v.event_title, v.description
                FROM TBL_DECEASED_VIDEO vm
                JOIN TBL_VIDEO v ON vm.id_metadata = v.id_video
                WHERE vm.id_deceased = %s
            """, [id])
            videos = [dict(zip(['id_metadata', 'video_link', 'event_title', 'description'], r)) for r in cursor.fetchall()]

        all_deceased = Deceased.objects.exclude(id_deceased=id)

    return render(request, 'edit_family_member.html', {
        'form': form,
        'miembro': miembro,
        'relaciones': relaciones,
        'imagenes': imagenes,
        'videos': videos,
        'all_deceased': all_deceased
    })


@login_required_auth0
def delete_family_member(request, id):
    miembro = get_object_or_404(Deceased, id_deceased=id)

    if request.method == 'POST':
        with connection.cursor() as cursor:
            # 1. Eliminar relaciones
            cursor.execute("DELETE FROM TBL_RELATION WHERE id_deceased = %s OR id_parent = %s", [id, id])

            # 2. Eliminar videos
            cursor.execute("""
                SELECT id_metadata FROM TBL_DECEASED_VIDEO WHERE id_deceased = %s
            """, [id])
            video_metadata_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute("DELETE FROM TBL_DECEASED_VIDEO WHERE id_deceased = %s", [id])
            for meta_id in video_metadata_ids:
                cursor.execute("DELETE FROM TBL_VIDEO WHERE id_video = %s", [meta_id])
                cursor.execute("DELETE FROM TBL_VIDEO_METADATA WHERE id_metadata = %s", [meta_id])

            # 3. Eliminar imágenes
            cursor.execute("""
                SELECT id_metadata FROM TBL_DECEASED_IMAGE WHERE id_deceased = %s
            """, [id])
            image_metadata_ids = [row[0] for row in cursor.fetchall()]

            cursor.execute("DELETE FROM TBL_DECEASED_IMAGE WHERE id_deceased = %s", [id])
            for meta_id in image_metadata_ids:
                cursor.execute("DELETE FROM TBL_IMAGE WHERE id_image = %s", [meta_id])
                cursor.execute("DELETE FROM TBL_IMAGE_METADATA WHERE id_metadata = %s", [meta_id])

            # 4. Eliminar acceso de usuarios
            cursor.execute("DELETE FROM TBL_USER_DECEASED WHERE id_deceased = %s", [id])

            # 5. Eliminar solicitudes y notificaciones relacionadas
            cursor.execute("DELETE FROM TBL_REQUEST WHERE id_deceased = %s", [id])

            # 6. Finalmente, eliminar al fallecido
            cursor.execute("DELETE FROM TBL_DECEASED WHERE id_deceased = %s", [id])

        return redirect('family_member_list')

    return render(request, 'delete_family_member.html', {'miembro': miembro})


# -------------------- REQUEST ACCESS & NOTIFICATIONS --------------------

@login_required_auth0
def request_access(request, id_deceased):
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM TBL_REQUEST
            WHERE id_issuer = %s AND id_deceased = %s AND request_status = 'pending'
        """, [user.id_user, id_deceased])
        if cursor.fetchone()[0] > 0:
            return redirect('family_member_list')

        cursor.execute("""
            SELECT id_user FROM TBL_USER_DECEASED
            WHERE id_deceased = %s AND has_permission = 1 LIMIT 1
        """, [id_deceased])
        creator_id = cursor.fetchone()[0]

        cursor.execute("""
            INSERT INTO TBL_REQUEST (id_issuer, id_receiver, id_deceased, creation_date, request_type, request_status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [user.id_user, creator_id, id_deceased, timezone.now(), 'view', 'pending'])
        request_id = cursor.lastrowid

        cursor.execute("""
            INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, creation_date)
            VALUES (%s, %s, %s, %s)
        """, [user.id_user, creator_id, f"{user.name} has requested access. Request #{request_id}", timezone.now()])
    return redirect('family_member_list')

@login_required_auth0
def approve_request(request, request_id, action):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_issuer, id_deceased FROM TBL_REQUEST WHERE id_request = %s
        """, [request_id])
        requester_id, deceased_id = cursor.fetchone()

        cursor.execute("""
            UPDATE TBL_REQUEST SET request_status = %s WHERE id_request = %s
        """, [action, request_id])

        if action == 'approved':
            cursor.execute("""
                INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
                VALUES (%s, %s, %s, %s)
            """, [requester_id, deceased_id, timezone.now(), 1])
            message = f"✅ Your request to access memory ID {deceased_id} was approved."
        else:
            message = f"❌ Your request to access memory ID {deceased_id} was rejected."

        cursor.execute("""
            INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, creation_date)
            VALUES (%s, %s, %s, %s)
        """, [0, requester_id, message, timezone.now()])
    return redirect('view_requests')

@login_required_auth0
def notifications(request):
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()
    notifications = []
    if user:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE TBL_NOTIFICATION SET is_read = 1 WHERE id_receiver = %s
            """, [user.id_user])
            cursor.execute("""
                SELECT * FROM TBL_NOTIFICATION WHERE id_receiver = %s ORDER BY creation_date DESC
            """, [user.id_user])
            notifications = cursor.fetchall()
    return render(request, 'notifications.html', {'notifications': notifications})

@login_required_auth0
def mark_notification_read(request, notification_id):
    user_session = request.session.get('user')
    user = User.objects.filter(email=user_session['email']).first()
    if user:
        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE TBL_NOTIFICATION SET is_read = 1 WHERE id_notification = %s AND id_receiver = %s
            """, [notification_id, user.id_user])
    return redirect('family_member_list')

@login_required_auth0
def handle_notification_action(request, notification_id, action):
    user_session = request.session.get('user')
    current_user = User.objects.filter(email=user_session['email']).first()

    if request.method == 'POST' and current_user:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id_sender, message FROM TBL_NOTIFICATION
                WHERE id_notification = %s AND id_receiver = %s
            """, [notification_id, current_user.id_user])
            notif = cursor.fetchone()

            if notif:
                sender_id, message = notif
                match = re.search(r"memory ID (\d+)", message)

                if match:
                    id_deceased = int(match.group(1))

                    if action == 'accept':
                        cursor.execute("""
                            INSERT IGNORE INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
                            VALUES (%s, %s, %s, %s)
                        """, [current_user.id_user, id_deceased, timezone.now(), 0])
                    # Ya sea accept, decline o read: marcar como leída
                cursor.execute("""
                    UPDATE TBL_NOTIFICATION SET is_read = 1 WHERE id_notification = %s
                """, [notification_id])
                connection.commit()  # <-- AÑADE ESTA LÍNEA

    return redirect('family_member_list')


@login_required_auth0
def approve_request(request, request_id, action):
    user_session = request.session.get('user')
    approver = User.objects.filter(email=user_session['email']).first()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id_issuer, id_deceased FROM TBL_REQUEST WHERE id_request = %s
        """, [request_id])
        requester_id, deceased_id = cursor.fetchone()

        cursor.execute("""
            UPDATE TBL_REQUEST SET request_status = %s WHERE id_request = %s
        """, [action, request_id])

        if action == 'approved':
            # Primero borramos si ya existe (prevención de duplicados)
            cursor.execute("""
                DELETE FROM TBL_USER_DECEASED WHERE id_user = %s AND id_deceased = %s
            """, [requester_id, deceased_id])

            cursor.execute("""
                INSERT INTO TBL_USER_DECEASED (id_user, id_deceased, date_relation, has_permission)
                VALUES (%s, %s, %s, %s)
            """, [requester_id, deceased_id, timezone.now(), 0])

            message = f"✅ Your request to access memory ID {deceased_id} was approved."
        else:
            message = f"❌ Your request to access memory ID {deceased_id} was rejected."

        cursor.execute("""
            INSERT INTO TBL_NOTIFICATION (id_sender, id_receiver, message, creation_date, is_read)
            VALUES (%s, %s, %s, %s, %s)
        """, [approver.id_user, requester_id, message, timezone.now(), 0])

    return redirect('family_member_list')


@require_GET
def ajax_search_deceased(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id_deceased, name FROM TBL_DECEASED
                WHERE LOWER(name) LIKE %s
                LIMIT 10
            """, [f"%{query.lower()}%"])
            rows = cursor.fetchall()
            for row in rows:
                results.append({
                    'id': row[0],
                    'name': row[1]
                })
    return JsonResponse({'results': results})