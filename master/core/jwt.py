from datetime import datetime, timedelta
from dateutils import relativedelta
from typing import Optional
import jwt

from master.core import arguments


def generate_jwt(payload: dict, expiration_minutes: int = 15, algorithm: Optional[str] = None) -> str:
    """
    Generates a JWT with the given payload and expiration.
    :param payload: Data to include in the JWT.
    :param algorithm: Signing algorithm (default is HS256).
    :param expiration_minutes: Expiration time in minutes (default is 15).
    :return: Encoded JWT as a string.
    """
    payload_copy = payload.copy()
    if expiration_minutes > 0:
        payload_copy['exp'] = datetime.utcnow() + timedelta(minutes=expiration_minutes)
    else:
        payload_copy['exp'] = datetime.utcnow() + relativedelta(years=1000)
    return jwt.encode(payload_copy, arguments['jwt_secret'], algorithm or 'HS256')


def validate_jwt(token: str, algorithms: Optional[list[str]] = None) -> dict:
    """
    Validates and decodes a JWT.
    :param token: The JWT to validate.
    :param algorithms: List of allowed algorithms.
    :return: Decoded payload if valid.
    :raises: jwt.ExpiredSignatureError, jwt.InvalidTokenError
    """
    algorithms = algorithms or ['HS256']
    try:
        return jwt.decode(token, arguments['jwt_secret'], algorithms=algorithms)
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token.")
