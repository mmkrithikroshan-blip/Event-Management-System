from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q, Min
from django.contrib import messages
from django.utils import timezone
from .models import Event, Category, City, ContactMessage
from .forms import ContactForm

def home_view(request):
    """
    Home page matching UI:
    - Hero banner: "Live the Moment - Book Your Favourite Events" + search bar
    - "Upcoming Events" section with cards + "View All ->" link
    """
    upcoming_events = Event.objects.filter(
        status='published',
        event_date__gte=timezone.now().date()
    ).select_related('category').prefetch_related('ticket_types').order_by('event_date')[:6]

    # In case there are no upcoming events yet in DB, show published events
    if not upcoming_events.exists():
        upcoming_events = Event.objects.filter(status='published').order_by('event_date')[:6]

    categories = Category.objects.all()
    cities = City.objects.all()

    return render(request, 'events/home.html', {
        'upcoming_events': upcoming_events,
        'categories': categories,
        'cities': cities,
    })

def event_list_view(request):
    """
    Paginated Events Listing with search and multi-criteria filters.
    FR-U3.1 - FR-U3.4
    """
    events = Event.objects.filter(status='published').select_related('category').prefetch_related('ticket_types')

    q = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    city_name = request.GET.get('city', '').strip()
    date_filter = request.GET.get('date', '').strip()
    sort_by = request.GET.get('sort', 'date_asc')

    if q:
        events = events.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(venue__icontains=q) |
            Q(city__icontains=q) |
            Q(organizer__icontains=q)
        )

    if category_slug:
        events = events.filter(category__slug=category_slug)

    if city_name:
        events = events.filter(city__iexact=city_name)

    if date_filter:
        try:
            parsed_date = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
            events = events.filter(event_date=parsed_date)
        except ValueError:
            pass

    # Sorting
    if sort_by == 'date_desc':
        events = events.order_by('-event_date')
    elif sort_by == 'price_asc':
        events = events.annotate(min_ticket_price=Min('ticket_types__price')).order_by('min_ticket_price')
    elif sort_by == 'price_desc':
        events = events.annotate(min_ticket_price=Min('ticket_types__price')).order_by('-min_ticket_price')
    else: # default date_asc
        events = events.order_by('event_date', 'start_time')

    paginator = Paginator(events, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    categories = Category.objects.all()
    cities = City.objects.all()

    return render(request, 'events/event_list.html', {
        'page_obj': page_obj,
        'events': page_obj,
        'categories': categories,
        'cities': cities,
        'current_q': q,
        'current_category': category_slug,
        'current_city': city_name,
        'current_date': date_filter,
        'current_sort': sort_by,
        'total_results': events.count()
    })

def event_detail_view(request, slug):
    """
    Event Details Page (FR-U4.1 - FR-U4.3)
    Shows title, banner, date, venue, ticket types, remaining availability, etc.
    """
    event = get_object_or_404(
        Event.objects.select_related('category', 'created_by').prefetch_related('ticket_types'),
        slug=slug
    )
    ticket_types = event.ticket_types.all()
    
    # Related events
    related_events = Event.objects.filter(
        category=event.category,
        status='published'
    ).exclude(id=event.id)[:3]

    return render(request, 'events/event_detail.html', {
        'event': event,
        'ticket_types': ticket_types,
        'related_events': related_events,
    })

def about_view(request):
    return render(request, 'events/about.html')

def contact_view(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Thank you! Your message has been sent successfully. We will get back to you shortly.")
            return redirect('events:contact')
    else:
        form = ContactForm()

    return render(request, 'events/contact.html', {'form': form})
