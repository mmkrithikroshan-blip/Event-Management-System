from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Administrator'),
        ('event_manager', 'Event Manager'),
        ('gate_staff', 'Gate Staff'),
    )

    email = models.EmailField(unique=True, verbose_name="Email Address")
    full_name = models.CharField(max_length=150, verbose_name="Full Name")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile Number")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    class Meta:
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    @property
    def is_administrator(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def is_event_manager(self):
        return self.role in ['admin', 'event_manager'] or self.is_superuser

    @property
    def is_gate_staff(self):
        return self.role in ['admin', 'gate_staff', 'event_manager'] or self.is_superuser

    @property
    def has_admin_access(self):
        return self.role in ['admin', 'event_manager', 'gate_staff'] or self.is_staff or self.is_superuser
