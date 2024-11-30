import threading
import signal
import logging
from functools import wraps
from typing import Callable, List

from master.tools.methods import call_method

_logger = logging.getLogger(__name__)
stop_event = threading.Event()


class ThreadManager:
    """
    A manager to handle threads that run tasks and stop gracefully
    when the main program receives a termination signal.
    """
    __slots__ = 'threads'

    def __init__(self):
        self.threads: List[threading.Thread] = []
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

    def add_thread(self, name: str, target: Callable, *args, **kwargs):
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

    def is_alive(self):
        return any(thread.is_alive() for thread in self.threads)


def worker(func: Callable):
    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        started = False
        while not stop_event.is_set():
            if not started:
                call_method(self, '_start')
                started = True
            func(self, *args, **kwargs)
        if started:
            call_method(self, '_destroy')
        class_name = func.__qualname__.split('.')[0] + '.' if '.' in func.__qualname__ else '.'
        _logger.info(f"Worker {func.__module__}.{class_name}{func.__name__} thread stopping gracefully.")
    return _wrapper
