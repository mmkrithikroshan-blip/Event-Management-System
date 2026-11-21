from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home_view, name='home'),
    path('events/', views.event_list_admin_view, name='events_list'),
    path('events/create/', views.event_create_view, name='event_create'),
    path('events/<int:event_id>/edit/', views.event_edit_view, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete_view, name='event_delete'),

    path('bookings/', views.booking_list_admin_view, name='bookings_list'),
    path('bookings/<str:booking_id>/', views.booking_detail_admin_view, name='booking_detail'),
    path('bookings/<str:booking_id>/cancel/', views.booking_cancel_admin_view, name='booking_cancel'),

    path('users/', views.user_list_admin_view, name='users_list'),
    path('users/<int:user_id>/toggle-status/', views.user_toggle_status_view, name='user_toggle_status'),
    path('users/<int:user_id>/change-role/', views.user_role_edit_view, name='user_role_edit'),

    path('payments/', views.payment_list_admin_view, name='payments_list'),
    path('payments/export/csv/', views.payment_export_csv_view, name='payment_export_csv'),

    path('reports/', views.reports_view, name='reports'),
    path('settings/', views.settings_view, name='settings'),

    path('scanner/', views.qr_scanner_view, name='qr_scanner'),
    path('api/validate-ticket/', views.validate_qr_api_view, name='validate_ticket_api'),
]
