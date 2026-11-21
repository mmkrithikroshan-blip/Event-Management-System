import csv
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.db import transaction

from accounts.models import User
from events.models import Event, Category, City, TicketType
from bookings.models import Booking, BookingItem, Ticket
from payments.models import Payment, Refund
from dashboard.models import SystemSetting, AuditLog
from dashboard.services.report_service import get_dashboard_metrics, log_audit

def admin_required(view_func):
    """Decorator ensuring only admin/event_manager/gate_staff can access"""
    def check_perms(user):
        return user.is_authenticated and (user.has_admin_access or user.is_staff or user.is_superuser)
    return user_passes_test(check_perms, login_url='accounts:login')(view_func)


@admin_required
def dashboard_home_view(request):
    """
    Main Admin Dashboard matching the UI mockup:
    - Summary Cards: Total Events, Total Bookings, Total Revenue
    - Sales Overview line chart
    - Recent Bookings list with status badges
    """
    metrics = get_dashboard_metrics()
    return render(request, 'dashboard/index.html', {
        'metrics': metrics,
        'active_menu': 'dashboard'
    })


@admin_required
def event_list_admin_view(request):
    """Admin event list with filters (FR-A3.4)"""
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    events = Event.objects.select_related('category').prefetch_related('ticket_types').order_by('-event_date')

    if q:
        events = events.filter(Q(title__icontains=q) | Q(city__icontains=q) | Q(venue__icontains=q))

    if status_filter:
        events = events.filter(status=status_filter)

    return render(request, 'dashboard/events_list.html', {
        'events': events,
        'q': q,
        'status_filter': status_filter,
        'active_menu': 'events'
    })


@admin_required
def event_create_view(request):
    """Add new event with ticket categories (FR-A3.1)"""
    categories = Category.objects.all()
    cities = City.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        category_id = request.POST.get('category_id')
        venue = request.POST.get('venue')
        city = request.POST.get('city')
        event_date = request.POST.get('event_date')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time') or None
        organizer = request.POST.get('organizer')
        banner_url = request.POST.get('banner_url', '')
        status = request.POST.get('status', 'published')
        featured = request.POST.get('featured') == 'on'

        banner_image = request.FILES.get('banner_image')

        category = get_object_or_404(Category, id=category_id)

        with transaction.atomic():
            event = Event.objects.create(
                title=title,
                description=description,
                category=category,
                venue=venue,
                city=city,
                event_date=event_date,
                start_time=start_time,
                end_time=end_time,
                organizer=organizer,
                banner_url=banner_url,
                banner_image=banner_image,
                status=status,
                featured=featured,
                created_by=request.user
            )

            # Process Ticket Types
            ticket_names = request.POST.getlist('ticket_name[]')
            ticket_prices = request.POST.getlist('ticket_price[]')
            ticket_quantities = request.POST.getlist('ticket_quantity[]')

            for name, price, qty in zip(ticket_names, ticket_prices, ticket_quantities):
                if name.strip() and price and qty:
                    TicketType.objects.create(
                        event=event,
                        name=name.strip(),
                        price=Decimal(price),
                        total_quantity=int(qty),
                        sold_quantity=0
                    )

            log_audit(request.user, 'CREATE_EVENT', 'Event', event.id, f"Created event {event.title}")
            messages.success(request, f"Event '{event.title}' created successfully!")
            return redirect('dashboard:events_list')

    return render(request, 'dashboard/event_form.html', {
        'categories': categories,
        'cities': cities,
        'active_menu': 'events',
        'is_edit': False
    })


@admin_required
def event_edit_view(request, event_id):
    """Edit event details & ticket types (FR-A3.2)"""
    event = get_object_or_404(Event.objects.prefetch_related('ticket_types'), id=event_id)
    categories = Category.objects.all()
    cities = City.objects.all()

    if request.method == 'POST':
        event.title = request.POST.get('title')
        event.description = request.POST.get('description')
        event.category = get_object_or_404(Category, id=request.POST.get('category_id'))
        event.venue = request.POST.get('venue')
        event.city = request.POST.get('city')
        event.event_date = request.POST.get('event_date')
        event.start_time = request.POST.get('start_time')
        event.end_time = request.POST.get('end_time') or None
        event.organizer = request.POST.get('organizer')
        event.banner_url = request.POST.get('banner_url', '')
        event.status = request.POST.get('status', 'published')
        event.featured = request.POST.get('featured') == 'on'

        if 'banner_image' in request.FILES:
            event.banner_image = request.FILES['banner_image']

        event.save()

        # Update ticket types
        ticket_ids = request.POST.getlist('ticket_id[]')
        ticket_names = request.POST.getlist('ticket_name[]')
        ticket_prices = request.POST.getlist('ticket_price[]')
        ticket_quantities = request.POST.getlist('ticket_quantity[]')

        for tid, name, price, qty in zip(ticket_ids, ticket_names, ticket_prices, ticket_quantities):
            if tid:
                tt = TicketType.objects.filter(id=tid, event=event).first()
                if tt:
                    tt.name = name.strip()
                    tt.price = Decimal(price)
                    tt.total_quantity = int(qty)
                    tt.save()
            elif name.strip() and price and qty:
                TicketType.objects.create(
                    event=event,
                    name=name.strip(),
                    price=Decimal(price),
                    total_quantity=int(qty)
                )

        log_audit(request.user, 'UPDATE_EVENT', 'Event', event.id, f"Updated event {event.title}")
        messages.success(request, f"Event '{event.title}' updated successfully!")
        return redirect('dashboard:events_list')

    return render(request, 'dashboard/event_form.html', {
        'event': event,
        'categories': categories,
        'cities': cities,
        'active_menu': 'events',
        'is_edit': True
    })


@admin_required
def event_delete_view(request, event_id):
    """Soft delete or archive event (FR-A3.2)"""
    event = get_object_or_404(Event, id=event_id)
    if event.bookings.filter(status='confirmed').exists():
        messages.warning(request, "This event has confirmed bookings. It cannot be deleted, but you may mark it Cancelled.")
        event.status = 'cancelled'
        event.save()
    else:
        event.delete()
        messages.success(request, "Event deleted successfully.")

    return redirect('dashboard:events_list')


@admin_required
def booking_list_admin_view(request):
    """Manage Bookings list with search & filters (FR-A5.1)"""
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    bookings = Booking.objects.select_related('event', 'user').prefetch_related('tickets').order_by('-created_at')

    if q:
        bookings = bookings.filter(
            Q(booking_id__icontains=q) |
            Q(user__full_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(event__title__icontains=q)
        )

    if status_filter:
        bookings = bookings.filter(status=status_filter)

    return render(request, 'dashboard/bookings_list.html', {
        'bookings': bookings,
        'q': q,
        'status_filter': status_filter,
        'active_menu': 'bookings'
    })


@admin_required
def booking_detail_admin_view(request, booking_id):
    """Admin view booking details (FR-A5.2)"""
    booking = get_object_or_404(
        Booking.objects.select_related('event', 'user').prefetch_related('items__ticket_type', 'tickets', 'payments'),
        booking_id=booking_id
    )
    return render(request, 'dashboard/booking_detail.html', {
        'booking': booking,
        'active_menu': 'bookings'
    })


@admin_required
def booking_cancel_admin_view(request, booking_id):
    """Admin cancels a booking & triggers refund record (FR-A5.3)"""
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Cancelled by administrator')

        with transaction.atomic():
            booking.status = 'cancelled'
            booking.cancellation_reason = reason
            booking.save(update_fields=['status', 'cancellation_reason'])

            # Restore tickets stock
            for item in booking.items.all():
                tt = item.ticket_type
                tt.sold_quantity = max(0, tt.sold_quantity - item.quantity)
                tt.save(update_fields=['sold_quantity'])

            # Create Refund record if paid
            payment = booking.payments.filter(status='paid').first()
            if payment:
                Refund.objects.create(
                    refund_id=f"REF-{booking.booking_id}",
                    payment=payment,
                    amount=payment.amount,
                    reason=reason,
                    status='processed'
                )
                payment.status = 'refunded'
                payment.save(update_fields=['status'])

            log_audit(request.user, 'ADMIN_CANCEL_BOOKING', 'Booking', booking.booking_id, f"Cancelled by admin: {reason}")
            messages.success(request, f"Booking #{booking.booking_id} cancelled and inventory restored.")

    return redirect('dashboard:booking_detail', booking_id=booking.booking_id)


@admin_required
def user_list_admin_view(request):
    """Manage Users (FR-A6.1 - FR-A6.3)"""
    q = request.GET.get('q', '')
    users = User.objects.all().order_by('-date_joined')

    if q:
        users = users.filter(Q(full_name__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q))

    return render(request, 'dashboard/users_list.html', {
        'users': users,
        'q': q,
        'active_menu': 'users'
    })


@admin_required
def user_toggle_status_view(request, user_id):
    """Activate or deactivate user account"""
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own account.")
    else:
        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=['is_active'])
        status_text = "activated" if target_user.is_active else "deactivated"
        log_audit(request.user, 'TOGGLE_USER_STATUS', 'User', target_user.id, f"Account {status_text}")
        messages.success(request, f"User {target_user.email} {status_text} successfully.")

    return redirect('dashboard:users_list')


@admin_required
def user_role_edit_view(request, user_id):
    """Change user role (Customer, Admin, Event Manager, Gate Staff)"""
    target_user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_role = request.POST.get('role')
        if new_role in ['customer', 'admin', 'event_manager', 'gate_staff']:
            target_user.role = new_role
            if new_role in ['admin', 'event_manager', 'gate_staff']:
                target_user.is_staff = True
            target_user.save()
            log_audit(request.user, 'CHANGE_USER_ROLE', 'User', target_user.id, f"Role changed to {new_role}")
            messages.success(request, f"Role for {target_user.email} updated to {target_user.get_role_display()}.")

    return redirect('dashboard:users_list')


@admin_required
def payment_list_admin_view(request):
    """Manage Payments & Transactions (FR-A7.1)"""
    q = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')

    payments = Payment.objects.select_related('booking__user', 'booking__event').order_by('-created_at')

    if q:
        payments = payments.filter(
            Q(payment_id__icontains=q) |
            Q(razorpay_payment_id__icontains=q) |
            Q(booking__booking_id__icontains=q)
        )

    if status_filter:
        payments = payments.filter(status=status_filter)

    return render(request, 'dashboard/payments_list.html', {
        'payments': payments,
        'q': q,
        'status_filter': status_filter,
        'active_menu': 'payments'
    })


@admin_required
def payment_export_csv_view(request):
    """Export payments list as CSV (FR-A7.2)"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="EventHub_Payments.csv"'

    writer = csv.writer(response)
    writer.writerow(['Payment ID', 'Booking ID', 'Customer', 'Event', 'Amount (INR)', 'Razorpay Payment ID', 'Status', 'Date'])

    for p in Payment.objects.select_related('booking__user', 'booking__event').order_by('-created_at'):
        writer.writerow([
            p.payment_id,
            p.booking.booking_id,
            p.booking.user.full_name or p.booking.user.email,
            p.booking.event.title,
            p.amount,
            p.razorpay_payment_id or 'N/A',
            p.status,
            p.created_at.strftime('%Y-%m-%d %H:%M')
        ])

    return response


@admin_required
def reports_view(request):
    """Analytics & Sales Reports (FR-A8.1 - FR-A8.3)"""
    events_report = Event.objects.annotate(
        total_bookings=Count('bookings', filter=Q(bookings__status='confirmed')),
        total_revenue=Sum('bookings__total_amount', filter=Q(bookings__status='confirmed'))
    ).order_by('-total_revenue')

    # Top selling events
    top_events = events_report[:5]

    return render(request, 'dashboard/reports.html', {
        'events_report': events_report,
        'top_events': top_events,
        'active_menu': 'reports'
    })


@admin_required
def settings_view(request):
    """Platform Configuration Settings (FR-A9.1)"""
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key != 'csrfmiddlewaretoken':
                setting, _ = SystemSetting.objects.get_or_create(key=key)
                setting.value = value
                setting.save()

        log_audit(request.user, 'UPDATE_SETTINGS', 'Setting', 'ALL', "Updated system settings")
        messages.success(request, "Settings updated successfully!")
        return redirect('dashboard:settings')

    settings_list = SystemSetting.objects.all()
    return render(request, 'dashboard/settings.html', {
        'settings_list': settings_list,
        'active_menu': 'settings'
    })


@admin_required
def qr_scanner_view(request):
    """
    Gate Staff QR Scanner interface (FR-Q1 - FR-Q4).
    Camera scanner + manual ticket code input.
    """
    events = Event.objects.filter(status='published').order_by('event_date')
    return render(request, 'dashboard/qr_scanner.html', {
        'events': events,
        'active_menu': 'scanner'
    })


@admin_required
def validate_qr_api_view(request):
    """
    AJAX API endpoint for instant ticket verification (FR-Q2, FR-Q3, FR-Q4).
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            raw_token = data.get('token', '').strip()
            event_id = data.get('event_id')

            # Clean raw token if prefix exists (e.g. EVENTHUB:TICKET:xxx)
            token = raw_token.replace('EVENTHUB:TICKET:', '').strip()

            ticket = Ticket.objects.select_related('booking__user', 'booking__event', 'ticket_type').filter(
                Q(qr_token=token) | Q(ticket_code=token)
            ).first()

            if not ticket:
                return JsonResponse({
                    'status': 'invalid',
                    'message': '❌ Invalid Ticket: No matching record found.',
                }, status=404)

            booking = ticket.booking

            # Check if booking cancelled
            if booking.status == 'cancelled':
                return JsonResponse({
                    'status': 'cancelled',
                    'message': f'⚠️ Booking #{booking.booking_id} was CANCELLED.',
                    'attendee': ticket.attendee_name,
                    'event': booking.event.title,
                })

            # Check if event matches (if event filter specified)
            if event_id and str(booking.event.id) != str(event_id):
                return JsonResponse({
                    'status': 'wrong_event',
                    'message': f'⚠️ Wrong Event! Ticket belongs to "{booking.event.title}", not selected event.',
                    'attendee': ticket.attendee_name,
                    'event': booking.event.title,
                })

            # Check if ticket already used
            if ticket.is_used:
                used_time = ticket.used_at.strftime('%d %b %Y at %I:%M %p') if ticket.used_at else 'Earlier'
                validator_name = ticket.validated_by.full_name if ticket.validated_by else 'Gate Staff'
                return JsonResponse({
                    'status': 'already_used',
                    'message': f'⚠️ Ticket ALREADY USED on {used_time} by {validator_name}.',
                    'attendee': ticket.attendee_name,
                    'ticket_code': ticket.ticket_code,
                    'event': booking.event.title,
                    'tier': ticket.ticket_type.name,
                })

            # Ticket is VALID! Mark it as used
            ticket.mark_used(validator_user=request.user)
            log_audit(request.user, 'VALIDATE_TICKET', 'Ticket', ticket.ticket_code, f"Validated entry for {ticket.attendee_name}")

            return JsonResponse({
                'status': 'success',
                'message': '✅ Entry Approved! Ticket is valid.',
                'attendee': ticket.attendee_name,
                'ticket_code': ticket.ticket_code,
                'event': booking.event.title,
                'tier': ticket.ticket_type.name,
                'booking_id': booking.booking_id,
                'validated_at': timezone.now().strftime('%d %b %Y at %I:%M %p')
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'method_not_allowed'}, status=405)
