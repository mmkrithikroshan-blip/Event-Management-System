import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from events.models import Event, TicketType

def generate_booking_code():
    last_booking = Booking.objects.order_by('-id').first()
    if not last_booking:
        return 'BK00101'
    return f"BK{last_booking.id + 101:05d}"

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('refunded', 'Refunded'),
    )

    booking_id = models.CharField(max_length=30, unique=True, default=generate_booking_code)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name='bookings')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    convenience_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_tickets = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    cancellation_reason = models.TextField(blank=True)
    held_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking_id} - {self.user.full_name or self.user.username} (₹{self.total_amount})"

    @property
    def is_hold_valid(self):
        if self.status != 'pending':
            return False
        if not self.held_until:
            return True
        return timezone.now() < self.held_until

    @property
    def status_badge_class(self):
        badges = {
            'confirmed': 'badge-success',
            'pending': 'badge-warning',
            'cancelled': 'badge-danger',
            'expired': 'badge-secondary',
            'refunded': 'badge-info'
        }
        return badges.get(self.status, 'badge-secondary')


class BookingItem(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='items')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.booking.booking_id} - {self.ticket_type.name} x {self.quantity}"


class Ticket(models.Model):
    ticket_code = models.CharField(max_length=50, unique=True)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='tickets')
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT)
    attendee_name = models.CharField(max_length=150)
    qr_token = models.CharField(max_length=120, unique=True, default=uuid.uuid4)
    pdf_file = models.FileField(upload_to='tickets/pdfs/', blank=True, null=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='validated_tickets'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['ticket_code']

    def __str__(self):
        return f"{self.ticket_code} ({self.attendee_name}) - {'USED' if self.is_used else 'VALID'}"

    def mark_used(self, validator_user=None):
        self.is_used = True
        self.used_at = timezone.now()
        if validator_user:
            self.validated_by = validator_user
        self.save(update_fields=['is_used', 'used_at', 'validated_by'])
