import os
import django
from decimal import Decimal
from datetime import date, time, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eventhub.settings')
django.setup()

from django.utils import timezone
from accounts.models import User
from events.models import Category, City, Event, TicketType
from bookings.models import Booking, BookingItem, Ticket
from payments.models import Payment
from dashboard.models import SystemSetting

def seed():
    print("🌱 Starting database seeding...")

    # 1. System Settings
    settings_data = {
        'site_name': 'EventHub',
        'convenience_fee_percent': '2.5',
        'tax_percent': '18.0',
        'hold_duration_minutes': '10',
        'contact_email': 'support@eventhub.com',
        'contact_phone': '+91 98765 43210',
        'currency_symbol': '₹',
    }
    for k, v in settings_data.items():
        SystemSetting.objects.update_or_create(key=k, defaults={'value': v})
    print("✓ System settings configured.")

    # 2. Users
    admin_user, _ = User.objects.get_or_create(
        email='admin@eventhub.com',
        defaults={
            'username': 'admin@eventhub.com',
            'full_name': 'EventHub Admin',
            'role': 'admin',
            'is_staff': True,
            'is_superuser': True,
            'mobile': '9876543210'
        }
    )
    admin_user.set_password('admin123')
    admin_user.role = 'admin'
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()

    customer_user, _ = User.objects.get_or_create(
        email='krithik@example.com',
        defaults={
            'username': 'krithik@example.com',
            'full_name': 'Krithik Roshan',
            'role': 'customer',
            'mobile': '9840123456'
        }
    )
    customer_user.set_password('user123')
    customer_user.save()

    staff_user, _ = User.objects.get_or_create(
        email='staff@eventhub.com',
        defaults={
            'username': 'staff@eventhub.com',
            'full_name': 'Gate Validator Staff',
            'role': 'gate_staff',
            'is_staff': True,
            'mobile': '9123456789'
        }
    )
    staff_user.set_password('staff123')
    staff_user.role = 'gate_staff'
    staff_user.is_staff = True
    staff_user.save()
    print("✓ Admin, customer and staff users created.")

    # 3. Categories
    cat_concerts, _ = Category.objects.get_or_create(
        slug='concerts',
        defaults={'name': 'Music Concerts', 'icon': 'bi-music-note-beamed', 'description': 'Live stadium concerts, rock, EDM, indie and acoustic tours.'}
    )
    cat_tech, _ = Category.objects.get_or_create(
        slug='tech-summits',
        defaults={'name': 'Tech Summits', 'icon': 'bi-laptop', 'description': 'Developer summits, AI conventions, startup keynotes.'}
    )
    cat_sports, _ = Category.objects.get_or_create(
        slug='sports',
        defaults={'name': 'Sports Championships', 'icon': 'bi-trophy-fill', 'description': 'Stadium athletics, tennis tournaments, and championship leagues.'}
    )
    cat_workshops, _ = Category.objects.get_or_create(
        slug='workshops',
        defaults={'name': 'Workshops & Arts', 'icon': 'bi-easel-fill', 'description': 'Creative bootcamps, masterclasses, and fine arts exhibitions.'}
    )
    print("✓ Categories created.")

    # 4. Cities
    cities_list = [
        ('Chennai', 'Tamil Nadu'),
        ('Bengaluru', 'Karnataka'),
        ('Mumbai', 'Maharashtra'),
        ('Delhi NCR', 'Delhi'),
        ('Hyderabad', 'Telangana')
    ]
    for c_name, c_state in cities_list:
        City.objects.get_or_create(name=c_name, defaults={'state': c_state})
    print("✓ Cities created.")

    # 5. Events (Exact match with UI mockup)
    # Event 1: Music Concert 2026 Chennai (Dec 20, 2026)
    e1, _ = Event.objects.get_or_create(
        slug='music-concert-2026-chennai',
        defaults={
            'title': 'Music Concert 2026 Chennai',
            'category': cat_concerts,
            'description': 'Experience the grandest musical extravaganza of the year in Chennai featuring world-renowned international and playback sensations. High-voltage audio-visuals, immersive stadium acoustics, and an unforgettable live crowd atmosphere.',
            'banner_url': 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200&q=80',
            'venue': 'Jawaharlal Nehru Stadium',
            'city': 'Chennai',
            'event_date': date(2026, 12, 20),
            'start_time': time(18, 0),
            'end_time': time(23, 0),
            'organizer': 'LiveNation India & Waves Media',
            'status': 'published',
            'featured': True,
            'created_by': admin_user
        }
    )
    tt1_gen, _ = TicketType.objects.get_or_create(event=e1, name='General Admission', defaults={'price': Decimal('1500.00'), 'total_quantity': 3500, 'sold_quantity': 420})
    tt1_vip, _ = TicketType.objects.get_or_create(event=e1, name='VIP Front Row', defaults={'price': Decimal('3500.00'), 'total_quantity': 800, 'sold_quantity': 180})
    tt1_vvip, _ = TicketType.objects.get_or_create(event=e1, name='VVIP Backstage Pass', defaults={'price': Decimal('7500.00'), 'total_quantity': 150, 'sold_quantity': 45})

    # Event 2: Tech Summit 2026 Chennai (Jan 15, 2027)
    e2, _ = Event.objects.get_or_create(
        slug='tech-summit-2026-chennai',
        defaults={
            'title': 'Tech Summit 2026 Chennai',
            'category': cat_tech,
            'description': 'The premier technology gathering uniting cloud architects, AI researchers, founders, and engineers. Join keynotes on generative AI, distributed systems, quantum computing, and future web frameworks.',
            'banner_url': 'https://images.unsplash.com/photo-1540575467063-178a50c2df87?auto=format&fit=crop&w=1200&q=80',
            'venue': 'Chennai Trade Centre, Nandambakkam',
            'city': 'Chennai',
            'event_date': date(2027, 1, 15),
            'start_time': time(9, 30),
            'end_time': time(17, 30),
            'organizer': 'Global Tech Guild & IEEE Madras',
            'status': 'published',
            'featured': True,
            'created_by': admin_user
        }
    )
    tt2_stu, _ = TicketType.objects.get_or_create(event=e2, name='Student Delegate', defaults={'price': Decimal('1000.00'), 'total_quantity': 600, 'sold_quantity': 210})
    tt2_pro, _ = TicketType.objects.get_or_create(event=e2, name='Professional Pass', defaults={'price': Decimal('2500.00'), 'total_quantity': 1200, 'sold_quantity': 450})
    tt2_all, _ = TicketType.objects.get_or_create(event=e2, name='All-Access VIP Delegate', defaults={'price': Decimal('5000.00'), 'total_quantity': 200, 'sold_quantity': 85})

    # Event 3: Sports Championship Chennai (Feb 10, 2027)
    e3, _ = Event.objects.get_or_create(
        slug='sports-championship-chennai',
        defaults={
            'title': 'Sports Championship Chennai',
            'category': cat_sports,
            'description': 'Witness top national and international champions compete for the prestigious championship trophy. High-octane matches, premier arena hospitality, and electrifying fan zones.',
            'banner_url': 'https://images.unsplash.com/photo-1508098682722-e99c43a406b2?auto=format&fit=crop&w=1200&q=80',
            'venue': 'SDAT Tennis Stadium, Nungambakkam',
            'city': 'Chennai',
            'event_date': date(2027, 2, 10),
            'start_time': time(16, 0),
            'end_time': time(21, 30),
            'organizer': 'Sports Development Authority of TN',
            'status': 'published',
            'featured': True,
            'created_by': admin_user
        }
    )
    tt3_std, _ = TicketType.objects.get_or_create(event=e3, name='Standard Stands', defaults={'price': Decimal('800.00'), 'total_quantity': 2000, 'sold_quantity': 650})
    tt3_crt, _ = TicketType.objects.get_or_create(event=e3, name='Courtside Premier', defaults={'price': Decimal('2000.00'), 'total_quantity': 500, 'sold_quantity': 190})

    # Additional Events in Bengaluru and Mumbai
    e4, _ = Event.objects.get_or_create(
        slug='bengaluru-rock-carnival-2027',
        defaults={
            'title': 'Bengaluru Rock & Indie Carnival 2027',
            'category': cat_concerts,
            'description': 'Indie bands, alternative rock icons, craft food pop-ups, and live acoustic open mic stages at the garden city.',
            'banner_url': 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?auto=format&fit=crop&w=1200&q=80',
            'venue': 'Palace Grounds, Jayamahal Road',
            'city': 'Bengaluru',
            'event_date': date(2027, 3, 5),
            'start_time': time(17, 0),
            'end_time': time(23, 0),
            'organizer': 'Bangalore Beats Ent.',
            'status': 'published',
            'created_by': admin_user
        }
    )
    TicketType.objects.get_or_create(event=e4, name='Festival Day Pass', defaults={'price': Decimal('1200.00'), 'total_quantity': 2500, 'sold_quantity': 300})

    e5, _ = Event.objects.get_or_create(
        slug='mumbai-ai-developers-conclave',
        defaults={
            'title': 'Mumbai AI & Cloud Developers Conclave',
            'category': cat_tech,
            'description': 'Hands-on architectural deep dives, LLM fine-tuning workshops, and networking sessions with top founders.',
            'banner_url': 'https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?auto=format&fit=crop&w=1200&q=80',
            'venue': 'Jio World Convention Centre, BKC',
            'city': 'Mumbai',
            'event_date': date(2027, 3, 22),
            'start_time': time(10, 0),
            'end_time': time(18, 0),
            'organizer': 'Mumbai Tech Circle',
            'status': 'published',
            'created_by': admin_user
        }
    )
    TicketType.objects.get_or_create(event=e5, name='Standard Delegate', defaults={'price': Decimal('2999.00'), 'total_quantity': 1000, 'sold_quantity': 150})
    print("✓ Events & Ticket Tiers seeded.")

    # 6. Recent Bookings (Exact match with UI mockup: BK00126, BK00125, BK00124)
    # BK00126 | ₹1,500 | Paid
    b126, _ = Booking.objects.get_or_create(
        booking_id='BK00126',
        defaults={
            'user': customer_user,
            'event': e1,
            'subtotal': Decimal('1440.00'),
            'convenience_fee': Decimal('50.85'),
            'tax_amount': Decimal('9.15'),
            'total_amount': Decimal('1500.00'),
            'total_tickets': 1,
            'status': 'confirmed'
        }
    )
    BookingItem.objects.get_or_create(booking=b126, ticket_type=tt1_gen, defaults={'quantity': 1, 'unit_price': Decimal('1440.00'), 'total_price': Decimal('1440.00')})
    Payment.objects.get_or_create(
        payment_id='PAY-BK00126-001',
        defaults={
            'booking': b126,
            'amount': Decimal('1500.00'),
            'status': 'paid',
            'razorpay_order_id': 'order_rzp_mock_126',
            'razorpay_payment_id': 'pay_rzp_live_126908',
            'paid_at': timezone.now() - timedelta(minutes=15)
        }
    )
    Ticket.objects.get_or_create(
        ticket_code='TKT-BK00126-01',
        defaults={
            'booking': b126,
            'ticket_type': tt1_gen,
            'attendee_name': customer_user.full_name,
            'qr_token': 'TOKEN-SECURE-BK00126-01-CHENNAI'
        }
    )

    # BK00125 | ₹2,000 | Paid
    b125, _ = Booking.objects.get_or_create(
        booking_id='BK00125',
        defaults={
            'user': customer_user,
            'event': e3,
            'subtotal': Decimal('1920.00'),
            'convenience_fee': Decimal('67.80'),
            'tax_amount': Decimal('12.20'),
            'total_amount': Decimal('2000.00'),
            'total_tickets': 1,
            'status': 'confirmed'
        }
    )
    BookingItem.objects.get_or_create(booking=b125, ticket_type=tt3_crt, defaults={'quantity': 1, 'unit_price': Decimal('1920.00'), 'total_price': Decimal('1920.00')})
    Payment.objects.get_or_create(
        payment_id='PAY-BK00125-001',
        defaults={
            'booking': b125,
            'amount': Decimal('2000.00'),
            'status': 'paid',
            'razorpay_order_id': 'order_rzp_mock_125',
            'razorpay_payment_id': 'pay_rzp_live_125442',
            'paid_at': timezone.now() - timedelta(hours=1)
        }
    )
    Ticket.objects.get_or_create(
        ticket_code='TKT-BK00125-01',
        defaults={
            'booking': b125,
            'ticket_type': tt3_crt,
            'attendee_name': customer_user.full_name,
            'qr_token': 'TOKEN-SECURE-BK00125-01-SPORTS'
        }
    )

    # BK00124 | ₹1,000 | Paid
    b124, _ = Booking.objects.get_or_create(
        booking_id='BK00124',
        defaults={
            'user': customer_user,
            'event': e2,
            'subtotal': Decimal('960.00'),
            'convenience_fee': Decimal('33.90'),
            'tax_amount': Decimal('6.10'),
            'total_amount': Decimal('1000.00'),
            'total_tickets': 1,
            'status': 'confirmed'
        }
    )
    BookingItem.objects.get_or_create(booking=b124, ticket_type=tt2_stu, defaults={'quantity': 1, 'unit_price': Decimal('960.00'), 'total_price': Decimal('960.00')})
    Payment.objects.get_or_create(
        payment_id='PAY-BK00124-001',
        defaults={
            'booking': b124,
            'amount': Decimal('1000.00'),
            'status': 'paid',
            'razorpay_order_id': 'order_rzp_mock_124',
            'razorpay_payment_id': 'pay_rzp_live_124119',
            'paid_at': timezone.now() - timedelta(hours=3)
        }
    )
    Ticket.objects.get_or_create(
        ticket_code='TKT-BK00124-01',
        defaults={
            'booking': b124,
            'ticket_type': tt2_stu,
            'attendee_name': customer_user.full_name,
            'qr_token': 'TOKEN-SECURE-BK00124-01-TECHSUMMIT'
        }
    )

    print("✓ Recent Bookings (BK00126, BK00125, BK00124) created.")
    print("🎉 Seeding completed successfully!")

if __name__ == '__main__':
    seed()
