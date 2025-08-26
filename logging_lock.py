import threading

# A global lock for all print and stdout operations to prevent interleaved messages
# from different threads and to handle encoding issues safely.
lock = threading.Lock()
