from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, FileResponse, Http404
from django.utils import timezone
from django.db import transaction
from events.models import Event, TicketType
from dashboard.models import SystemSetting
from dashboard.services.report_service import log_audit
from .models import Booking, BookingItem, Ticket
from .services.ticket_service import generate_ticket_pdf

@login_required
def select_tickets_view(request, slug):
    """
    Select ticket categories and quantities (FR-U5.1 - FR-U5.5).
    Enforces maximum quantity per booking (max 10) and stock limits.
    """
    event = get_object_or_404(Event, slug=slug, status='published')

    if request.method == 'POST':
        ticket_type_id = request.POST.get('ticket_type_id')
        quantity_str = request.POST.get('quantity', '1')

        try:
            quantity = int(quantity_str)
        except ValueError:
            quantity = 1

        if quantity < 1 or quantity > 10:
            messages.error(request, "You can book between 1 and 10 tickets per order.")
            return redirect('events:event_detail', slug=event.slug)

        try:
            with transaction.atomic():
                ticket_type = TicketType.objects.select_for_update().get(id=ticket_type_id, event=event)
                if ticket_type.available_quantity < quantity:
                    messages.error(request, f"Sorry, only {ticket_type.available_quantity} tickets are available for {ticket_type.name}.")
                    return redirect('events:event_detail', slug=event.slug)

                # Fee calculation
                unit_price = ticket_type.price
                subtotal = unit_price * quantity
                fee_pct = Decimal(SystemSetting.get_val('convenience_fee_percent', '2.5'))
                convenience_fee = round(subtotal * (fee_pct / Decimal('100.0')), 2)
                tax_amount = round(convenience_fee * Decimal('0.18'), 2) # 18% GST on convenience fee
                total_amount = subtotal + convenience_fee + tax_amount

                hold_minutes = int(SystemSetting.get_val('hold_duration_minutes', '10'))
                held_until = timezone.now() + timezone.timedelta(minutes=hold_minutes)

                booking = Booking.objects.create(
                    user=request.user,
                    event=event,
                    subtotal=subtotal,
                    convenience_fee=convenience_fee,
                    tax_amount=tax_amount,
                    total_amount=total_amount,
                    total_tickets=quantity,
                    status='pending',
                    held_until=held_until
                )

                BookingItem.objects.create(
                    booking=booking,
                    ticket_type=ticket_type,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=subtotal
                )

                log_audit(request.user, 'CREATE_BOOKING_INIT', 'Booking', booking.booking_id, f"Held {quantity} tickets for {event.title}")
                return redirect('bookings:booking_summary', booking_id=booking.booking_id)

        except TicketType.DoesNotExist:
            messages.error(request, "Selected ticket type is invalid.")
            return redirect('events:event_detail', slug=event.slug)

    return redirect('events:event_detail', slug=event.slug)


@login_required
def booking_summary_view(request, booking_id):
    """
    Booking summary with pricing breakdown & hold timer (FR-U5.3).
    """
    booking = get_object_or_404(
        Booking.objects.select_related('event', 'user').prefetch_related('items__ticket_type'),
        booking_id=booking_id,
        user=request.user
    )

    if booking.status == 'confirmed':
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)

    # Check hold expiry
    if booking.status == 'pending' and booking.held_until and timezone.now() > booking.held_until:
        booking.status = 'expired'
        booking.save(update_fields=['status'])
        messages.warning(request, "Your ticket hold session has expired. Please select your tickets again.")
        return redirect('events:event_detail', slug=booking.event.slug)

    seconds_remaining = 0
    if booking.held_until:
        remaining = (booking.held_until - timezone.now()).total_seconds()
        seconds_remaining = max(0, int(remaining))

    return render(request, 'bookings/booking_summary.html', {
        'booking': booking,
        'items': booking.items.all(),
        'seconds_remaining': seconds_remaining
    })


@login_required
def booking_history_view(request):
    """
    Customer booking history (FR-U8.1 - FR-U8.3).
    """
    bookings = Booking.objects.filter(user=request.user).select_related('event').order_by('-created_at')
    return render(request, 'bookings/my_bookings.html', {
        'bookings': bookings
    })


@login_required
def booking_detail_view(request, booking_id):
    """
    Detailed booking confirmation and status view (FR-U8.2).
    """
    if request.user.has_admin_access:
        booking = get_object_or_404(
            Booking.objects.select_related('event', 'user').prefetch_related('items__ticket_type', 'tickets'),
            booking_id=booking_id
        )
    else:
        booking = get_object_or_404(
            Booking.objects.select_related('event', 'user').prefetch_related('items__ticket_type', 'tickets'),
            booking_id=booking_id,
            user=request.user
        )

    return render(request, 'bookings/booking_detail.html', {
        'booking': booking,
        'tickets': booking.tickets.all()
    })


@login_required
def download_ticket_pdf_view(request, booking_id):
    """
    Generates and downloads PDF ticket with QR code (FR-U7.1 - FR-U7.4).
    """
    if request.user.has_admin_access:
        booking = get_object_or_404(Booking, booking_id=booking_id)
    else:
        booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    if booking.status != 'confirmed':
        messages.error(request, "Ticket PDF is only available for paid and confirmed bookings.")
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)

    pdf_buffer = generate_ticket_pdf(booking)
    filename = f"EventHub_Ticket_{booking.booking_id}.pdf"
    return FileResponse(pdf_buffer, as_attachment=True, filename=filename)


@login_required
def cancel_booking_request_view(request, booking_id):
    """
    User requests booking cancellation per policy (FR-U8.3).
    """
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)

    if booking.status != 'confirmed':
        messages.error(request, "Only confirmed bookings can be cancelled.")
        return redirect('bookings:booking_detail', booking_id=booking.booking_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Cancelled by customer')
        
        with transaction.atomic():
            booking.status = 'cancelled'
            booking.cancellation_reason = reason
            booking.save(update_fields=['status', 'cancellation_reason'])

            # Restore inventory
            for item in booking.items.all():
                tt = item.ticket_type
                tt.sold_quantity = max(0, tt.sold_quantity - item.quantity)
                tt.save(update_fields=['sold_quantity'])

            # Log audit
            log_audit(request.user, 'USER_CANCEL_BOOKING', 'Booking', booking.booking_id, f"Cancelled with reason: {reason}")
            messages.success(request, f"Booking #{booking.booking_id} has been cancelled successfully.")
            return redirect('bookings:my_bookings')

    return render(request, 'bookings/cancel_confirm.html', {'booking': booking})
