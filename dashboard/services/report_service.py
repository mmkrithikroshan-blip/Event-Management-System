from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
from events.models import Event, Category
from bookings.models import Booking, Ticket
from payments.models import Payment, Refund
from dashboard.models import AuditLog

def log_audit(actor, action, entity, entity_id, details=''):
    try:
        AuditLog.objects.create(
            actor=actor if (actor and actor.is_authenticated) else None,
            action=action,
            entity=entity,
            entity_id=str(entity_id),
            details=details
        )
    except Exception:
        pass

def get_dashboard_metrics():
    total_events = Event.objects.count()
    confirmed_bookings = Booking.objects.filter(status='confirmed')
    total_bookings = confirmed_bookings.count()
    
    # Total revenue from confirmed bookings or completed payments
    revenue_agg = Payment.objects.filter(status='paid').aggregate(total=Sum('amount'))
    total_revenue = revenue_agg['total'] or 0

    if total_revenue == 0 and total_bookings > 0:
        total_revenue = confirmed_bookings.aggregate(total=Sum('total_amount'))['total'] or 0

    # Recent bookings (up to 6)
    recent_bookings = Booking.objects.select_related('event', 'user').order_by('-created_at')[:8]

    # Month-wise sales overview for line chart (Jan - Dec)
    current_year = timezone.now().year
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_sales = [0] * 12
    monthly_bookings = [0] * 12

    for month_idx in range(1, 13):
        m_payments = Payment.objects.filter(
            status='paid',
            created_at__year=current_year,
            created_at__month=month_idx
        ).aggregate(total=Sum('amount'))['total'] or 0

        m_b_count = Booking.objects.filter(
            status='confirmed',
            created_at__year=current_year,
            created_at__month=month_idx
        ).count()

        monthly_sales[month_idx - 1] = float(m_payments)
        monthly_bookings[month_idx - 1] = m_b_count

    return {
        'total_events': total_events,
        'total_bookings': total_bookings,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'months_labels': month_names[:6], # Jan to Jun for compact chart or all 12
        'all_months_labels': month_names,
        'monthly_sales': monthly_sales[:6],
        'all_monthly_sales': monthly_sales,
        'monthly_bookings': monthly_bookings[:6],
    }
