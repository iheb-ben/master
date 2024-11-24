from typing import Optional
import socket
import uuid
import requests


def get_public_ip(raise_error: bool = True) -> Optional[str]:
    """
    Fetches the public IP address of the machine using an external service.
    Args:
        raise_error (bool): If true trigger error in case request failed
    Returns:
        str: The public IP address of the machine.
    Raises:
        SystemError: If there's an issue fetching the public IP address.
    """
    try:
        response = requests.get('https://api.ipify.org?format=text', timeout=5)
        if response.status_code == 200:
            return response.text
        else:
            raise requests.RequestException(f'Endpoint returned status {response.status_code}')
    except requests.RequestException as e:
        if raise_error:
            raise SystemError(f'Error fetching public IP: {e}')
        return None


def get_mac_address() -> str:
    """
    Retrieves the MAC address of the machine.
    Returns:
        str: The MAC address formatted as a colon-separated string.
    """
    mac = uuid.getnode()
    return ':'.join(f"{(mac >> ele) & 0xff:02x}" for ele in range(0, 8 * 6, 8))[::-1]


def get_private_ip(raise_error: bool = True) -> Optional[str]:
    """
    Fetches the private IP address of the machine.
    Args:
        raise_error (bool): If true trigger error in case request failed
    Returns:
        str: The private IP address of the machine.
    Raises:
        SystemError: If there's an issue fetching the private IP address.
    """
    try:
        hostname = socket.gethostname()
        private_ip = socket.gethostbyname(hostname)
        return private_ip
    except socket.error as e:
        if raise_error:
            raise SystemError(f'Error fetching private IP: {e}')
        return None
