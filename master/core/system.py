import subprocess
import os
import signal
import logging

_logger = logging.getLogger(__name__)


class ProcessManager:
    __slots__ = ('command', 'process')

    def __init__(self, command):
        """
        Initialize the ProcessManager with a command to run.
        :param command: A list of command arguments to execute the process.
        """
        self.command = command
        self.process = None

    def start_process(self):
        """
        Start the process using the given command.
        """
        if self.process is None or self.process.poll() is not None:
            self.process = subprocess.Popen(self.command)
            _logger.info(f"Process started with PID: {self.process.pid}")
        else:
            _logger.info("Process is already running.")

    def terminate_process(self):
        """
        Terminate the process if it is running.
        """
        if self.process and self.process.poll() is None:
            _logger.info(f"Terminating process with PID: {self.process.pid}")
            self.process.terminate()
            self.process.wait()  # Ensure process is terminated
            _logger.info("Process terminated.")
        else:
            _logger.info("No running process to terminate.")

    def kill_process(self):
        """
        Kill the process forcefully if it is running.
        """
        if self.process and self.process.poll() is None:
            _logger.info(f"Killing process with PID: {self.process.pid}")
            os.kill(self.process.pid, signal.SIGKILL)
            self.process.wait()
            _logger.info("Process killed.")
        else:
            _logger.info("No running process to kill.")

    def is_running(self):
        """
        Check if the process is running.
        :return: True if running, False otherwise.
        """
        if self.process and self.process.poll() is None:
            _logger.info(f"Process with PID: {self.process.pid} is running.")
            return True
        _logger.info("Process is not running.")
        return False
