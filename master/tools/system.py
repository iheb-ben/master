"""
This module provides utility functions to check the validity and availability of ports
on the local machine. It includes functionality to find an available port within
the allowed range of 1 to 65535.

Functions:
- port_in_range: Checks if a port number is within the valid range (1-65535).
- port_is_available: Checks if a specific port is available for binding on localhost.
- find_available_port: Finds the next available port starting from a given number.

Global Variables:
- _already_checked_ports: A set to keep track of ports that have already been checked.
"""

import socket
import subprocess
import psutil


def get_max_threads_windows():
    virtual_memory = psutil.virtual_memory()
    total_memory = virtual_memory.total
    thread_stack_size = 2 * 1024 * 1024
    max_threads = total_memory // thread_stack_size
    return max_threads


# noinspection PyBroadException
def get_max_threads():
    try:
        result = subprocess.run(['ulimit', '-u'], capture_output=True, text=True, shell=True)
        return int(result.stdout.strip())
    except Exception:
        return get_max_threads_windows()


# A global set to store already checked ports to avoid redundant checks
_already_checked_ports = set()


def port_in_range(port: int) -> bool:
    """
    Check if the given port number is within the valid range of 1 to 65535.
    Args:
        port (int): The port number to check.
    Returns:
        bool: True if the port is in the valid range, False otherwise.
    """
    return 1 <= port <= 65535


def port_is_available(port: int) -> bool:
    """
    Check if the specified port is available for use on localhost.
    This function attempts to bind a socket to the specified port. If the binding
    succeeds, the port is available; otherwise, it is not.
    Args:
        port (int): The port number to check.
    Returns:
        bool: True if the port is available, False otherwise.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", port))  # Attempt to bind the socket
        return True  # Binding succeeded
    except OSError:
        return False  # Binding failed


def find_available_port(port: int) -> int:
    """
    Find the next available port starting from the given port number.
    This function iterates from the given port number and checks if the port
    is available. If the port is unavailable or invalid, it moves to the next
    port number. Ports that have already been checked are stored in a global set
    to avoid redundant checks.
    Args:
        port (int): The starting port number to check.
    Returns:
        int: The next available port number.
    Raises:
        OSError: If no valid port is found within the range or the provided port
                 is invalid.
    """
    while True:
        # Skip already-checked ports
        if port in _already_checked_ports:
            port += 1
            continue
        # Validate port range
        if not port_in_range(port):
            raise OSError(f'Invalid port {port}')
        # Check port availability
        if not port_is_available(port):
            _already_checked_ports.add(port)  # Mark the port as checked
            port += 1
        else:
            break  # Port is available
    return port
