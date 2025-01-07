import datetime
from typing import Tuple
from flask import request
from app import config


def client_public_ip():
    """Extract the client's IP address, considering proxy/forwarding."""
    if "X-Forwarded-For" in request.headers:
        # Use the first IP in the X-Forwarded-For list
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    if "X-Real-IP" in request.headers:
        return request.headers["X-Real-IP"]
    # Fallback to remote address
    return request.remote_addr


def token_expiration_date() -> Tuple[datetime.datetime, datetime.datetime]:
    current_date = datetime.datetime.utcnow()
    return current_date, current_date + datetime.timedelta(hours=config.JWT_ACCESS_TOKEN_EXPIRES)
