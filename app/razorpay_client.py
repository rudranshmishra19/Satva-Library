import os
import logging
import razorpay
import requests
from requests.exceptions import ConnectionError, RequestException
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class DummyRazorpayClient:
    class DummyOrder:
        def create(self, data):
            logger.warning("Using dummy Razorpay client - payment functionality disabled")
            return {"id": "dummy_order_id", "amount": data["amount"], "currency": data["currency"]}

    class DummyUtility:
        def verify_payment_signature(self, params):
            logger.warning("Signature verification skipped - using dummy client")

    def __init__(self):
        self.order = self.DummyOrder()
        self.utility = self.DummyUtility()


def get_razorpay_client():
    key_id = os.environ.get("KEY_ID")
    key_secret = os.environ.get("KEY_SECRET")

    if not key_id or not key_secret:
        logger.error("Razorpay credentials not found in environment variables")
        return DummyRazorpayClient()

    # Create a requests session with retry logic
    requests_session = requests.Session()
    for adapter in requests_session.adapters.values():
        adapter.max_retries = 3

    client = razorpay.Client(auth=(key_id, key_secret))
    # Optionally set custom session or transports if needed here

    return client


# Create a reusable Razorpay client instance
razorpay_client = get_razorpay_client()
