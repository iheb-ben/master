import threading
import signal
import time
import logging
from functools import wraps
from typing import Callable

_logger = logging.getLogger(__name__)
stop_event = threading.Event()


class ThreadManager:
    """
    A manager to handle threads that run tasks and stop gracefully
    when the main program receives a termination signal.
    """
    __slots__ = 'threads'

    def __init__(self):
        self.threads = []
        # Attach signal handlers for SIGINT and SIGTERM
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _signal_handler(self, signum, *args):
        """
        Signal handler to stop all threads when the program is terminated.
        """
        _logger.info(f"Signal {signum} received. Stopping all threads.")
        stop_event.set()

    def add_thread(self, name, target, *args, **kwargs):
        """
        Add a new thread to the manager.
        :param name: The thread name.
        :param target: The function the thread will execute.
        :param args: Positional arguments for the target function.
        :param kwargs: Keyword arguments for the target function.
        """
        thread = threading.Thread(name=name, target=target, args=args, kwargs=kwargs)
        self.threads.append(thread)
        return thread

    def start_all(self):
        """
        Start all managed threads.
        """
        for thread in self.threads:
            thread.start()

    def wait_for_all(self):
        """
        Wait for all threads to complete. This method blocks until
        all threads are terminated.
        """
        for thread in self.threads:
            thread.join()


def worker(func: Callable):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        while not stop_event.is_set():
            func(*args, **kwargs)
        _logger.info(f"Worker {func.__module__}.{func.__name__} thread stopping gracefully.")
    return _wrapper
