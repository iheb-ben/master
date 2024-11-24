import socket

already_checked = set()


def find_available_port(port: int) -> int:
    """
    Checks if a port is available. If the provided port is in use,
    increments the port number by 1 and checks again until an available port is found.
    Args:
        port (int): The starting port number to check for availability.
    Returns:
        int: An available port number.
    Example:
        >>> find_available_port(9000)
        9000  # or the next available port if 9000 is in use
    """
    while True:
        if port in already_checked:
            port += 1
            continue
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
            break
        except OSError:
            already_checked.add(port)
            port += 1
    return port
