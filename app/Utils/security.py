import base64
import hashlib
import hmac
import os
import smtplib
import time
from email.mime.text import MIMEText

import bcrypt
import pyotp
from dateutil.parser import parse
from dotenv import load_dotenv
from flask import jsonify, request

from ..db.connection import r


def rate_limit(length: int):
    """
    Rate limiter function
    """

    ip = request.remote_addr

    # If an ip address is not recieved throw an error
    if not ip:
        return jsonify({"error": "Rate limited Unable to process request address"}), 429

    # Check if the user has made more than the required amounts of requests within 10 seconds
    timestamp = time.time()
    values = r.zrangebyscore(ip, timestamp, "+inf")

    if len(values) > length:
        return jsonify({"error": "Rate limited too many requests"}), 429

    # Stores the time the requests were made to the ip address that made the request
    ttl_seconds = 10
    expire_at = time.time() + ttl_seconds
    r.zadd(ip, {f"request{timestamp}": expire_at})

    # Removes expired requests
    r.zremrangebyscore(ip, "-inf", timestamp)


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")  # store this safely in .env
EMAIL_USER = os.getenv("EMAIL_ADDR")
EMAIL_PASS = os.getenv("EMAIL_PW")


def generate_otp(email):
    """Generate a 6-digit time-based OTP for a specific email"""
    h = hmac.new(SECRET_KEY.encode(), email.encode(), hashlib.sha256)
    digest = h.digest()
    user_secret = base64.b32encode(digest).decode()
    totp = pyotp.TOTP(user_secret, digits=6, interval=120)
    return totp.now()


def verify_otp(email, otp):
    """Verify the OTP entered by the user"""
    h = hmac.new(SECRET_KEY.encode(), email.encode(), hashlib.sha256)
    digest = h.digest()
    user_secret = base64.b32encode(digest).decode()
    totp = pyotp.TOTP(user_secret, digits=6, interval=120)
    return totp.verify(otp)


def send_otp_mail(email, otp):
    """Send OTP to user's email"""
    msg = MIMEText(f"This is your OTP to verify your account: {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = EMAIL_USER
    msg["To"] = email

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False


salt = bcrypt.gensalt()


def hash_password(password):
    """Create password hash"""

    hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    return hashed


def verify(password, hashed):
    """Verify password hash"""
    check = bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    return check


def is_valid_date(date):
    try:
        parsed_date = parse(date)
        return parsed_date
    except Exception:
        return None
