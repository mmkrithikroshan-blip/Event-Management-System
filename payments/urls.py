from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/<str:booking_id>/', views.initiate_payment_view, name='initiate'),
    path('callback/', views.payment_callback_view, name='callback'),
    path('failed/<str:booking_id>/', views.payment_failed_view, name='payment_failed'),
    path('webhooks/razorpay/', views.razorpay_webhook_view, name='razorpay_webhook'),
]
