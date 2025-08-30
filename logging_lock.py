import threading
import time
import sys

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
