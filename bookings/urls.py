from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('select-tickets/<slug:slug>/', views.select_tickets_view, name='select_tickets'),
    path('summary/<str:booking_id>/', views.booking_summary_view, name='booking_summary'),
    path('history/', views.booking_history_view, name='my_bookings'),
    path('detail/<str:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('download-ticket/<str:booking_id>/', views.download_ticket_pdf_view, name='download_ticket_pdf'),
    path('cancel/<str:booking_id>/', views.cancel_booking_request_view, name='cancel_booking'),
]
