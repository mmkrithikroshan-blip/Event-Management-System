from dashboard.models import SystemSetting
from events.models import Category

def global_context(request):
    categories = Category.objects.all()[:8]
    site_name = SystemSetting.get_val('site_name', 'EventHub')
    contact_phone = SystemSetting.get_val('contact_phone', '+91 98765 43210')
    contact_email = SystemSetting.get_val('contact_email', 'contact@eventhub.com')
    currency_symbol = SystemSetting.get_val('currency_symbol', '₹')

    return {
        'SITE_NAME': site_name,
        'CONTACT_PHONE': contact_phone,
        'CONTACT_EMAIL': contact_email,
        'CURRENCY_SYMBOL': currency_symbol,
        'NAV_CATEGORIES': categories,
    }
