import threading
import signal
import logging
import time
from functools import wraps
from typing import Callable, List, Dict

from master.tools.methods import call_method

_logger = logging.getLogger(__name__)
stop_event = threading.Event()
started_threads: Dict[threading.Thread, bool] = {}


class ThreadManager:
    """
    A manager to handle threads that run tasks and stop gracefully
    when the main program receives a termination signal.
    """
    __slots__ = '_threads'
    allow = threading.Event()

    def __init__(self):
        self._threads: List[threading.Thread] = []
        # Attach signal handlers for SIGINT and SIGTERM
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def _signal_handler(self, signum, *args):
        """
        Signal handler to stop all threads when the program is terminated.
        """
        _logger.debug(f"Signal {signum} received. Stopping all threads.")
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
        self._threads.append(thread)
        return thread

    def start_all(self):
        """
        Start all managed threads.
        """
        for thread in self._threads:
            if thread.is_alive():
                continue
            thread.start()
            print_debug_message = False
            while not started_threads.get(thread):
                if not print_debug_message:
                    _logger.debug(f'Waiting for thread "{thread.name}" to start')
                    print_debug_message = True
                time.sleep(1)

    def is_alive(self):
        return any(thread.is_alive() for thread in self._threads)


def worker(func: Callable):
    @wraps(func)
    def _wrapper(self, *args, **kwargs):
        current = threading.current_thread()
        started_threads[current] = False
        while not stop_event.is_set():
            if not started_threads[current]:
                call_method(self, '_start')
                started_threads[current] = True
            if ThreadManager.allow.is_set():
                func(self, *args, **kwargs)
            else:
                time.sleep(1)
        if started_threads[current]:
            call_method(self, '_destroy')
            started_threads[current] = False
        _logger.debug(f"Worker {func.__module__}.{func.__qualname__} thread stopping gracefully.")
    return _wrapper
