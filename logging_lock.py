import threading
import time
import sys
import os
import logging
from logging.handlers import RotatingFileHandler

# A global lock for all print and stdout operations to prevent interleaved messages
# from different threads and to handle encoding issues safely.
lock = threading.Lock()

def get_timestamp():
    """Returns a formatted timestamp string."""
    return f"[{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}]::"

def console_log(message: str):
    """
    Prints a message to the console in a thread-safe manner, with a timestamp.
    """
    with lock:
        log_line = f"{get_timestamp()}{message}\n"
        sys.stdout.buffer.write(log_line.encode('utf-8', 'backslashreplace'))
        sys.stdout.flush()

class FileLogger:
    def __init__(self, user_id: str, provider_name: str, log_directory: str = "log"):
        self.user_id = user_id
        self.provider_name = provider_name
        self.log_directory = log_directory
        self._setup_loggers()

    def _setup_loggers(self):
        # Ensure the log directory exists
        os.makedirs(self.log_directory, exist_ok=True)

        # General logger for all providers
        self.all_providers_logger = self._create_logger(
            "all_providers",
            os.path.join(self.log_directory, "all_providers.log")
        )

        # Specific logger for this user/provider instance
        log_filename = f"{self.provider_name}_{self.user_id}.log"
        self.specific_logger = self._create_logger(
            f"{self.provider_name}_{self.user_id}",
            os.path.join(self.log_directory, log_filename)
        )

    def _create_logger(self, name: str, log_file: str) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # Prevent logs from propagating to the root logger
        logger.propagate = False

        # If handlers are already present, don't add them again
        if logger.hasHandlers():
            return logger

        # Use a rotating file handler to limit log file size
        handler = RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=2, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def log(self, message: str):
        # Log to both the general and the specific log file
        self.all_providers_logger.info(f"[{self.provider_name.upper()}:{self.user_id}] {message}")
        self.specific_logger.info(message)
