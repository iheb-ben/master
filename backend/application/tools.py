import datetime
import hmac
import hashlib
import base64
from typing import Tuple
from flask import request
from application import config


def generate_secret_string(input_string: str) -> str:
    """
    Generates a secure secret string using HMAC and a secret key.
    Args:
        input_string (str): The input string to be secured.
    Returns:
        str: A base64-encoded secret string.
    """
    # Encode the input string and secret key to bytes
    input_bytes = input_string.encode('utf-8')
    secret_bytes = config.JWT_SECRET_KEY.encode('utf-8')
    # Create HMAC object using SHA256
    hmac_obj = hmac.new(secret_bytes, input_bytes, hashlib.sha256)
    # Generate the digest and encode it in base64 for readability
    return base64.urlsafe_b64encode(hmac_obj.digest()).decode('utf-8')


def client_public_ip():
    """Extract the client's IP address, considering proxy/forwarding."""
    client_ip = request.headers.get('X-Real-IP') or request.remote_addr
    forwarded_header = request.headers.get('X-Forwarded-For') or ''
    if 'X-Real-IP' not in request.headers:
        for ip_address in forwarded_header.split(','):
            if ip_address and not ip_address.isspace():
                return ip_address
    return client_ip


def token_expiration_date() -> Tuple[datetime.datetime, datetime.datetime]:
    current_date = datetime.datetime.utcnow()
    return current_date, current_date + datetime.timedelta(hours=config.JWT_ACCESS_TOKEN_EXPIRES)


def current_user_id():
    try:
        return request.user.id
    except (RuntimeError, AttributeError):
        from application.utils.setup import SUPER_USER_ID
        return SUPER_USER_ID
