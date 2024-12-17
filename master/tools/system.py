import socket
import subprocess
from typing import Generator
import psutil


# noinspection PyBroadException
def get_max_threads() -> int:
    """
    Determines the maximum number of threads that can be created on the current system.
    On non-Windows systems, it tries to use the 'ulimit' command.
    On Windows, it calculates the limit based on available memory and stack size.

    Returns:
        int: The maximum number of threads supported by the system.
    """

    def _get_max_threads_windows():
        from master.core import arguments
        virtual_memory = psutil.virtual_memory()
        return virtual_memory.total // (arguments['thread_stack_size'] or 2 * 1024 * 1024)

    try:
        result = subprocess.run(['ulimit', '-u'], capture_output=True, text=True, shell=True)
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip())
    except Exception:
        pass
    try:
        return _get_max_threads_windows()
    except Exception:
        return 1


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


def generate_file_stream(file_path: str, chunk_size: int = 1024) -> Generator[bytes, None, None]:
    """
    Generate file content in chunks to stream it efficiently.
    :param file_path: Path to the file to be streamed.
    :param chunk_size: Size of each chunk in bytes.
    :yield: Chunk of file content.
    """
    with open(file_path, 'rb') as file:
        while chunk := file.read(chunk_size):
            yield chunk
