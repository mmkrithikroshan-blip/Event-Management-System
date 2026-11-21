import json
import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from bookings.models import Booking, Ticket
from .models import Payment, Refund
from .services.razorpay_service import create_order, verify_signature
from dashboard.services.report_service import log_audit

@login_required
def initiate_payment_view(request, booking_id):
    """
    Creates Razorpay order and renders checkout interface (FR-U6.1).
    """
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    if booking.status == 'confirmed':
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)

    # Check if hold expired
    if booking.held_until and timezone.now() > booking.held_until:
        booking.status = 'expired'
        booking.save(update_fields=['status'])
        messages.error(request, "Ticket reservation expired. Please restart your booking.")
        return redirect('events:event_detail', slug=booking.event.slug)

    # Create order via service
    order_data = create_order(
        amount=booking.total_amount,
        receipt=booking.booking_id,
        notes={'booking_id': booking.booking_id, 'event': booking.event.title}
    )

    # Create or update payment record
    payment_obj, _ = Payment.objects.get_or_create(
        booking=booking,
        status='created',
        defaults={
            'payment_id': f"PAY-{booking.booking_id}-{uuid.uuid4().hex[:6].upper()}",
            'amount': booking.total_amount,
            'razorpay_order_id': order_data['order_id']
        }
    )
    payment_obj.razorpay_order_id = order_data['order_id']
    payment_obj.save(update_fields=['razorpay_order_id'])

    return render(request, 'payments/razorpay_checkout.html', {
        'booking': booking,
        'order': order_data,
        'payment': payment_obj,
        'razorpay_key': settings.RAZORPAY_KEY_ID,
        'is_mock_enabled': settings.RAZORPAY_MOCK_MODE or order_data.get('is_mock', False),
    })


@csrf_exempt
@login_required
def payment_callback_view(request):
    """
    Processes Razorpay payment callback & verifies signature (FR-U6.3).
    Marks booking confirmed and generates unique QR tickets.
    """
    if request.method == 'POST':
        order_id = request.POST.get('razorpay_order_id', '')
        payment_id = request.POST.get('razorpay_payment_id', '')
        signature = request.POST.get('razorpay_signature', '')
        booking_id = request.POST.get('booking_id', '')

        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
        payment = Payment.objects.filter(booking=booking, razorpay_order_id=order_id).first()
        if not payment:
            payment = Payment.objects.filter(booking=booking).first()

        is_valid = verify_signature(order_id, payment_id, signature)

        if is_valid:
            with transaction.atomic():
                # 1. Update Payment
                if payment:
                    payment.razorpay_payment_id = payment_id
                    payment.razorpay_signature = signature
                    payment.status = 'paid'
                    payment.paid_at = timezone.now()
                    payment.save()

                # 2. Update Booking
                booking.status = 'confirmed'
                booking.held_until = None
                booking.save(update_fields=['status', 'held_until'])

                # 3. Permanently decrement stock
                for item in booking.items.all():
                    tt = item.ticket_type
                    tt.sold_quantity += item.quantity
                    tt.save(update_fields=['sold_quantity'])

                # 4. Generate individual Ticket instances with unique QR tokens
                # Clean old tickets if any
                booking.tickets.all().delete()
                ticket_index = 1
                for item in booking.items.all():
                    for _ in range(item.quantity):
                        t_code = f"TKT-{booking.booking_id}-{ticket_index:02d}"
                        Ticket.objects.create(
                            ticket_code=t_code,
                            booking=booking,
                            ticket_type=item.ticket_type,
                            attendee_name=request.user.full_name or request.user.username,
                            qr_token=f"{uuid.uuid4().hex[:16]}-{booking.booking_id}-{ticket_index}"
                        )
                        ticket_index += 1

                log_audit(request.user, 'PAYMENT_SUCCESS', 'Booking', booking.booking_id, f"Payment verified ₹{booking.total_amount}. Ref: {payment_id}")

            messages.success(request, f"🎉 Payment successful! Your booking #{booking.booking_id} is confirmed. Download your QR ticket below.")
            return redirect('bookings:booking_detail', booking_id=booking.booking_id)
        else:
            if payment:
                payment.status = 'failed'
                payment.error_description = "Signature verification failed"
                payment.save()
            messages.error(request, "Payment verification failed. Please try again.")
            return redirect('payments:payment_failed', booking_id=booking.booking_id)

    return redirect('home')


@login_required
def payment_failed_view(request, booking_id):
    """
    Payment failure / cancellation view (FR-U6.5).
    """
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, 'payments/payment_failed.html', {'booking': booking})


@csrf_exempt
def razorpay_webhook_view(request):
    """
    Razorpay Webhook endpoint to ensure idempotent payment confirmation (FR-U6.4).
    """
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            event = payload.get('event')
            # Handle payment.captured
            if event == 'payment.captured':
                payment_entity = payload.get('payload', {}).get('payment', {}).get('entity', {})
                order_id = payment_entity.get('order_id')
                payment_id = payment_entity.get('id')
                
                payment = Payment.objects.filter(razorpay_order_id=order_id).first()
                if payment and payment.status != 'paid':
                    booking = payment.booking
                    with transaction.atomic():
                        payment.status = 'paid'
                        payment.razorpay_payment_id = payment_id
                        payment.paid_at = timezone.now()
                        payment.save()

                        booking.status = 'confirmed'
                        booking.held_until = None
                        booking.save()

                        for item in booking.items.all():
                            tt = item.ticket_type
                            tt.sold_quantity += item.quantity
                            tt.save()
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return HttpResponse(status=405)
