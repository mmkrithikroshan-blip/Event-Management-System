from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from datetime import datetime

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, default='bi-tag', help_text='Bootstrap or font-awesome icon name')
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name_plural = 'Cities'
        ordering = ['name']

    def __str__(self):
        return self.name


class Event(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='events')
    banner_image = models.ImageField(upload_to='events/banners/', blank=True, null=True)
    banner_url = models.URLField(max_length=500, blank=True, help_text="Fallback image URL if banner is not uploaded")
    venue = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    event_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    organizer = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    featured = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['event_date', 'start_time']

    def __str__(self):
        return f"{self.title} - {self.city} ({self.event_date})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            count = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        return self.event_date >= timezone.now().date() and self.status == 'published'

    @property
    def min_price(self):
        types = self.ticket_types.all()
        if types.exists():
            return min(t.price for t in types)
        return 0

    @property
    def total_capacity(self):
        return sum(t.total_quantity for t in self.ticket_types.all())

    @property
    def total_sold(self):
        return sum(t.sold_quantity for t in self.ticket_types.all())

    @property
    def available_seats(self):
        return max(0, self.total_capacity - self.total_sold)

    @property
    def is_sold_out(self):
        return self.total_capacity > 0 and self.available_seats <= 0

    @property
    def sell_through_percentage(self):
        if self.total_capacity == 0:
            return 0
        return round((self.total_sold / self.total_capacity) * 100, 1)

    @property
    def display_banner(self):
        if self.banner_image:
            return self.banner_image.url
        if self.banner_url:
            return self.banner_url
        return 'https://images.unsplash.com/photo-1492684223066-81342ee5ff30?auto=format&fit=crop&w=1000&q=80'


class TicketType(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    name = models.CharField(max_length=100) # e.g. General, VIP, Early Bird
    description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_quantity = models.PositiveIntegerField()
    sold_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('event', 'name')
        ordering = ['price']

    def __str__(self):
        return f"{self.event.title} - {self.name} (₹{self.price})"

    @property
    def available_quantity(self):
        return max(0, self.total_quantity - self.sold_quantity)

    @property
    def is_sold_out(self):
        return self.available_quantity <= 0


class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name}: {self.subject}"
