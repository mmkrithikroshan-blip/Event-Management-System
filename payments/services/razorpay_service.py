import hmac
import hashlib
import uuid
import razorpay
from django.conf import settings

def get_razorpay_client():
    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        try:
            return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        except Exception:
            return None
    return None

def create_order(amount, receipt, notes=None):
    """
    Creates an order on Razorpay.
    Amount passed in INR (Decimal or float), converted to paise (integer).
    """
    amount_in_paise = int(round(float(amount) * 100))
    client = get_razorpay_client()

    if client and not settings.RAZORPAY_MOCK_MODE:
        try:
            data = {
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': receipt,
                'notes': notes or {},
                'payment_capture': 1
            }
            order = client.order.create(data=data)
            return {
                'order_id': order['id'],
                'amount': amount,
                'amount_paise': amount_in_paise,
                'currency': 'INR',
                'is_mock': False
            }
        except Exception as e:
            # Fallback to mock order if credentials invalid or offline
            pass

    # Mock order for demo/testing without live internet/sandbox credentials
    mock_order_id = f"order_mock_{uuid.uuid4().hex[:14]}"
    return {
        'order_id': mock_order_id,
        'amount': amount,
        'amount_paise': amount_in_paise,
        'currency': 'INR',
        'is_mock': True
    }

def verify_signature(order_id, payment_id, signature):
    """
    Verify payment signature using HMAC SHA256 as required by Razorpay.
    """
    if str(order_id).startswith('order_mock_'):
        # In mock demo mode, allow valid simulation
        return True

    client = get_razorpay_client()
    if client:
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            return True
        except Exception:
            # Fall back to manual HMAC calculation
            msg = f"{order_id}|{payment_id}"
            secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
            generated_signature = hmac.new(secret, msg.encode('utf-8'), hashlib.sha256).hexdigest()
            return hmac.compare_digest(generated_signature, signature)

    return False
