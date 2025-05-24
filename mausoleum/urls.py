from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Authentication
    path('', views.auth0_login, name='auth0_login'),  # raíz para login (redirige a Auth0)
    path('login/', views.auth0_login, name='auth0_login'),
    path('callback/', views.callback, name='callback'),
    path('logout/', views.auth0_logout, name='auth0_logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Deceased family members
    path('add/', views.add_family_member, name='add_family_member'),
    path('edit/<int:id>/', views.edit_family_member, name='edit_family_member'),
    path('delete/<int:id>/', views.delete_family_member, name='delete_family_member'),
    path('memories/', views.family_member_list, name='family_member_list'),
    path('share/<int:id>/', views.share_family_member, name='share_family_member'),
    path('ajax/search_deceased/', views.ajax_search_deceased, name='ajax_search_deceased'),

    # Access control
    path('request-access/<int:id_deceased>/', views.request_access, name='request_access'),
    path('approve-request/<int:request_id>/<str:action>/', views.approve_request, name='approve_request'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('notification-action/<int:notification_id>/<str:action>/', views.handle_notification_action, name='handle_notification_action'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
