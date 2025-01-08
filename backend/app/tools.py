import datetime
from typing import Tuple
from flask import request
from app import config


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
