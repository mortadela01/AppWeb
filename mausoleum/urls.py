from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Autenticación
    path('', views.auth0_login, name='auth0_login'),
    path('callback/', views.callback, name='callback'),
    path('login/', views.auth0_login, name='auth0_login'),
    path('logout/', views.auth0_logout, name='auth0_logout'),

    # Familiares fallecidos
    path('dashboard/', views.dashboard, name='dashboard'),  # puede ser el inicio
    path('add/', views.add_family_member, name='add_family_member'),  # ¡Ahora add es agregar familiar!
    path('edit/<int:id>/', views.edit_family_member, name='edit_family_member'),
    path('delete/<int:id>/', views.delete_family_member, name='delete_family_member'),
    path('memories/', views.family_member_list, name='family_member_list'),
    path('share/<int:id>/', views.share_family_member, name='share_family_member'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
