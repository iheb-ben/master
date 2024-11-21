import socket
import uuid
import requests


def get_public_ip() -> str:
    """
    Fetches the public IP address of the machine using an external service.
    Returns:
        str: The public IP address of the machine.
    Raises:
        SystemError: If there's an issue fetching the public IP address.
    """
    try:
        response = requests.get('https://api.ipify.org?format=text', timeout=5)
        return response.text
    except requests.RequestException as e:
        raise SystemError(f'Error fetching public IP: {e}')


def get_mac_address() -> str:
    """
    Retrieves the MAC address of the machine.
    Returns:
        str: The MAC address formatted as a colon-separated string.
    """
    mac = uuid.getnode()
    return ':'.join(f"{(mac >> ele) & 0xff:02x}" for ele in range(0, 8 * 6, 8))[::-1]


def get_private_ip() -> str:
    """
    Fetches the private IP address of the machine.
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
        raise SystemError(f'Error fetching private IP: {e}')
