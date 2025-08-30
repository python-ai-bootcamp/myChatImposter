import time
import threading
import subprocess
import json
import sys
import base64
import socket
import os
import uuid
from typing import Dict, Optional
import urllib.request
import urllib.error

# Assuming queue_manager.py is in the parent directory or accessible
from queue_manager import UserQueue, Sender, Group, Message
from logging_lock import lock

from .base import BaseChatProvider

def find_free_port():
    """Finds a free port on the host machine."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]

class WhatsAppBaileysProvider(BaseChatProvider):
    """
    A provider that connects to a Node.js Baileys server to send and receive WhatsApp messages.
    """
    def __init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue]):
        """
        Initializes the provider.
        - user_id: The specific user this provider instance is for.
        - config: The 'provider_config' block from the JSON configuration.
        - user_queues: A dictionary of all user queues, passed by the main application.
        """
        super().__init__(user_id, config, user_queues)
        self.is_listening = False
        self.thread = None
        self.node_process = None

        # Dynamically find a free port for the Node.js server to listen on.
        # This prevents port conflicts when running multiple vendor instances.
        self.port = find_free_port()
        self.base_url = f"http://localhost:{self.port}"

        # Start the Node.js server as a subprocess in an isolated directory
        try:
            # Create a deterministic working directory for this provider instance to allow for session persistence.
            self.work_dir = os.path.abspath(os.path.join('running_sessions', self.user_id))
            os.makedirs(self.work_dir, exist_ok=True)

            with lock:
                log_message = f"PROVIDER ({self.user_id}): Starting Node.js server on port {self.port} in CWD: {self.work_dir}\n"
                sys.stdout.buffer.write(log_message.encode('utf-8'))
                sys.stdout.flush()

            # Serialize and encode the config to pass as a command line argument
            config_json = json.dumps(self.config)
            config_base64 = base64.b64encode(config_json.encode('utf-8')).decode('utf-8')

            # The path to server.js must be absolute so it can be found from the new CWD
            server_script = os.path.abspath("chat_providers/whatsapp_baileys_server/server.js")

            self.node_process = subprocess.Popen(
                ['node', server_script, str(self.port), self.user_id, config_base64],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.work_dir  # Set the current working directory for the subprocess
            )
            # Thread to print server output for debugging
            threading.Thread(target=self._log_subprocess_output, daemon=True).start()
            with lock:
                sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Node.js server process started (PID: {self.node_process.pid}).\n".encode('utf-8'))
                sys.stdout.flush()
        except FileNotFoundError:
            with lock:
                sys.stdout.buffer.write(f"PROVIDER_ERROR ({self.user_id}): 'node' command not found. Please ensure Node.js is installed and in your PATH.\n".encode('utf-8'))
                sys.stdout.flush()
            raise
        except Exception as e:
            with lock:
                error_str = f"PROVIDER_ERROR ({self.user_id}): Failed to start Node.js server: {e}\n"
                sys.stdout.buffer.write(error_str.encode('utf-8', 'backslashreplace'))
                sys.stdout.flush()
            raise

    def _log_subprocess_output(self):
        """
        Logs the combined stdout and stderr from the Node.js subprocess for debugging.
        This method reads the subprocess output line by line to prevent garbled logs,
        and uses a lock to ensure writes to stdout are atomic.
        """
        if self.node_process.stdout:
            prefix = f"NODE_SERVER ({self.user_id}): ".encode('utf-8')
            line_buffer = bytearray()
            for byte in iter(lambda: self.node_process.stdout.read(1), b''):
                line_buffer.extend(byte)
                if byte == b'\n':
                    with lock:
                        sys.stdout.buffer.write(prefix)
                        sys.stdout.buffer.write(line_buffer)
                    try:
                        sys.stdout.flush()
                    except OSError:
                        pass
                    line_buffer.clear()
            # If the process exits without a final newline, print remaining buffer
            if line_buffer:
                with lock:
                    sys.stdout.buffer.write(prefix)
                    sys.stdout.buffer.write(line_buffer)
                    sys.stdout.buffer.write(b'\n') # Add a newline for clarity
                try:
                    sys.stdout.flush()
                except OSError:
                    pass

    def start_listening(self):
        """Starts the message listening loop in a background thread."""
        if self.is_listening:
            with lock:
                sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Already listening.\n".encode('utf-8'))
                sys.stdout.flush()
            return

        self.is_listening = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        with lock:
            sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Started polling for messages from Node.js server.\n".encode('utf-8'))
            sys.stdout.flush()

    def stop_listening(self):
        """Stops the message listening loop and terminates the Node.js server."""
        with lock:
            sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Stopping...\n".encode('utf-8'))
            sys.stdout.flush()
        self.is_listening = False
        if self.thread:
            # The thread will exit on its own since it checks `is_listening`
            self.thread.join() # Wait for the listening thread to finish
            with lock:
                sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Polling thread stopped.\n".encode('utf-8'))
                sys.stdout.flush()

        if self.node_process:
            with lock:
                sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Terminating Node.js server process (PID: {self.node_process.pid})...\n".encode('utf-8'))
                sys.stdout.flush()
            self.node_process.terminate()
            self.node_process.wait()
            with lock:
                sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Node.js server process terminated.\n".encode('utf-8'))
                sys.stdout.flush()

    def _listen(self):
        """
        The actual listening loop. It polls the Node.js server's /messages
        endpoint to fetch incoming WhatsApp messages.
        """
        while self.is_listening:
            try:
                # Add a timeout to prevent the thread from blocking indefinitely
                with urllib.request.urlopen(f"{self.base_url}/messages", timeout=10) as response:
                    if response.status == 200:
                        messages = json.loads(response.read().decode('utf-8'))
                        if messages:
                            with lock:
                                sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Fetched {len(messages)} new message(s).\n".encode('utf-8'))
                                sys.stdout.flush()
                            queue = self.user_queues.get(self.user_id)
                            if queue:
                                for msg in messages:
                                    # The message format is { sender, message, timestamp, group? }

                                    # Check if group messages are allowed
                                    allow_groups = self.config.get('allow_group_messages', True)
                                    group_info = msg.get('group')
                                    if group_info and not allow_groups:
                                        with lock:
                                            sys.stdout.buffer.write(f"PROVIDER ({self.user_id}): Ignoring message from group {group_info.get('id')} as per configuration.\n".encode('utf-8', 'backslashreplace'))
                                            sys.stdout.flush()
                                        continue

                                    sender = Sender(identifier=msg['sender'], display_name=msg.get('display_name', msg['sender']))
                                    group = Group(identifier=group_info['id'], display_name=group_info.get('name') or group_info['id']) if group_info else None

                                    queue.add_message(
                                        content=msg['message'],
                                        sender=sender,
                                        source='user',
                                        group=group
                                        # originating_time might need parsing from timestamp if needed
                                    )
                            else:
                                with lock:
                                    sys.stdout.buffer.write(f"PROVIDER_ERROR ({self.user_id}): Could not find a queue for myself.\n".encode('utf-8'))
                                    sys.stdout.flush()
                    else:
                        with lock:
                            sys.stdout.buffer.write(f"PROVIDER_ERROR ({self.user_id}): Error polling for messages. Status: {response.status}\n".encode('utf-8'))
                            sys.stdout.flush()
            except urllib.error.URLError as e:
                # This is expected if the server is not up yet, so don't spam the log
                time.sleep(2) # Wait a bit longer if server is not reachable
                continue
            except Exception as e:
                with lock:
                    error_message = f"PROVIDER_ERROR ({self.user_id}): Exception while polling for messages: {e}\n"
                    # Write directly to the buffer to avoid encoding errors on non-UTF-8 consoles
                    sys.stdout.buffer.write(error_message.encode('utf-8', 'backslashreplace'))
                    sys.stdout.flush()

            time.sleep(5) # Poll every 5 seconds

    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message back to the user via the Node.js server.
        """
        with lock:
            log_message = f"PROVIDER ({self.user_id}): Sending reply to {recipient} ---> {message[:50]}...\n"
            sys.stdout.buffer.write(log_message.encode('utf-8', 'backslashreplace'))
            sys.stdout.flush()
        try:
            data = json.dumps({"recipient": recipient, "message": message}).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/send",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    with lock:
                        body = response.read().decode('utf-8', 'backslashreplace')
                        sys.stdout.buffer.write(f"PROVIDER_ERROR ({self.user_id}): Failed to send message. Status: {response.status}, Body: {body}\n".encode('utf-8'))
                        sys.stdout.flush()
        except Exception as e:
            with lock:
                error_str = f"PROVIDER_ERROR ({self.user_id}): Exception while sending message: {e}\n"
                sys.stdout.buffer.write(error_str.encode('utf-8', 'backslashreplace'))
                sys.stdout.flush()

    def get_status(self) -> Dict:
        """
        Gets the connection status from the Node.js server.
        """
        try:
            with urllib.request.urlopen(f"{self.base_url}/status", timeout=5) as response:
                if response.status == 200:
                    return json.loads(response.read().decode('utf-8'))
                else:
                    return {"status": "error", "message": f"Failed to get status, HTTP {response.status}"}
        except urllib.error.URLError as e:
            # This can happen if the server is not yet running, which is a valid state
            return {"status": "initializing", "message": "Node.js server is not reachable yet."}
        except Exception as e:
            return {"status": "error", "message": f"Exception while getting status: {e}"}
