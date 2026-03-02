import random
from datetime import datetime, timedelta
from app.core.security import hash_password, verify_password

def generate_otp():
    return str(random.randint(100000, 999999))

def get_otp_expiry():
    return datetime.utcnow() + timedelta(minutes=10)
