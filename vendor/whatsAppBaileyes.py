import time
import threading
import subprocess
import json
import sys
import base64
from typing import Dict, Optional
import urllib.request
import urllib.error

# Assuming queue_manager.py is in the parent directory or accessible
from queue_manager import UserQueue, Sender, Group, Message

class Vendor:
    """
    A vendor that connects to a Node.js Baileys server to send and receive WhatsApp messages.
    """
    def __init__(self, user_id: str, config: Dict, user_queues: Dict[str, UserQueue]):
        """
        Initializes the vendor.
        - user_id: The specific user this vendor instance is for.
        - config: The 'vendor_config' block from the JSON configuration. Must contain 'port'.
        - user_queues: A dictionary of all user queues, passed by the Orchestrator.
        """
        self.user_id = user_id
        self.config = config
        self.user_queues = user_queues
        self.is_listening = False
        self.thread = None
        self.node_process = None

        self.port = self.config.get('port')
        if not self.port:
            raise ValueError(f"Port not specified in vendor_config for user {self.user_id}")

        self.base_url = f"http://localhost:{self.port}"

        # Start the Node.js server as a subprocess
        try:
            print(f"VENDOR ({self.user_id}): Starting Node.js server on port {self.port}...")

            # Serialize and encode the config to pass as a command line argument
            config_json = json.dumps(self.config)
            config_base64 = base64.b64encode(config_json.encode('utf-8')).decode('utf-8')

            # We need to make sure the server script is found relative to the project root
            server_script = "vendor/whatsapp_baileys_server/server.js"
            self.node_process = subprocess.Popen(
                ['node', server_script, str(self.port), self.user_id, config_base64],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            # Thread to print server output for debugging
            threading.Thread(target=self._log_subprocess_output, daemon=True).start()
            print(f"VENDOR ({self.user_id}): Node.js server process started (PID: {self.node_process.pid}).")
        except FileNotFoundError:
            print(f"VENDOR_ERROR ({self.user_id}): 'node' command not found. Please ensure Node.js is installed and in your PATH.")
            raise
        except Exception as e:
            print(f"VENDOR_ERROR ({self.user_id}): Failed to start Node.js server: {e}")
            raise

    def _log_subprocess_output(self):
        """
        Logs the combined stdout and stderr from the Node.js subprocess for debugging.
        The output is read byte by byte to prevent buffering issues, especially with QR codes,
        and then re-assembled into lines to maintain readable log output.
        """
        if self.node_process.stdout:
            prefix = f"NODE_SERVER ({self.user_id}): ".encode('utf-8')
            sys.stdout.buffer.write(prefix)
            for byte in iter(lambda: self.node_process.stdout.read(1), b''):
                sys.stdout.buffer.write(byte)
                if byte == b'\n':
                    sys.stdout.buffer.flush()
                    sys.stdout.buffer.write(prefix)
            sys.stdout.buffer.flush()

    def start_listening(self):
        """Starts the message listening loop in a background thread."""
        if self.is_listening:
            print(f"VENDOR ({self.user_id}): Already listening.")
            return

        self.is_listening = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
        print(f"VENDOR ({self.user_id}): Started polling for messages from Node.js server.")

    def stop_listening(self):
        """Stops the message listening loop and terminates the Node.js server."""
        print(f"VENDOR ({self.user_id}): Stopping...")
        self.is_listening = False
        if self.thread:
            # The thread will exit on its own since it checks `is_listening`
            self.thread.join() # Wait for the listening thread to finish
            print(f"VENDOR ({self.user_id}): Polling thread stopped.")

        if self.node_process:
            print(f"VENDOR ({self.user_id}): Terminating Node.js server process (PID: {self.node_process.pid})...")
            self.node_process.terminate()
            self.node_process.wait()
            print(f"VENDOR ({self.user_id}): Node.js server process terminated.")

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
                            print(f"VENDOR ({self.user_id}): Fetched {len(messages)} new message(s).")
                            queue = self.user_queues.get(self.user_id)
                            if queue:
                                for msg in messages:
                                    # The message format is { sender, message, timestamp, group? }

                                    # Check if group messages are allowed
                                    allow_groups = self.config.get('allow_group_messages', True)
                                    group_info = msg.get('group')
                                    if group_info and not allow_groups:
                                        sys.stdout.buffer.write(f"VENDOR ({self.user_id}): Ignoring message from group {group_info.get('id')} as per configuration.\n".encode('utf-8'))
                                        continue

                                    sender = Sender(identifier=msg['sender'], display_name=msg.get('display_name', msg['sender']))
                                    group = Group(identifier=group_info['id'], display_name=group_info.get('name')) if group_info else None

                                    queue.add_message(
                                        content=msg['message'],
                                        sender=sender,
                                        source='user',
                                        group=group
                                        # originating_time might need parsing from timestamp if needed
                                    )
                            else:
                                print(f"VENDOR_ERROR ({self.user_id}): Could not find a queue for myself.")
                    else:
                        print(f"VENDOR_ERROR ({self.user_id}): Error polling for messages. Status: {response.status}")
            except urllib.error.URLError as e:
                # This is expected if the server is not up yet, so don't spam the log
                time.sleep(2) # Wait a bit longer if server is not reachable
                continue
            except Exception as e:
                error_message = f"VENDOR_ERROR ({self.user_id}): Exception while polling for messages: {e}\n"
                # Write directly to the buffer to avoid encoding errors on non-UTF-8 consoles
                sys.stdout.buffer.write(error_message.encode('utf-8'))

            time.sleep(5) # Poll every 5 seconds

    def sendMessage(self, recipient: str, message: str):
        """
        Sends a message back to the user via the Node.js server.
        """
        print(f"VENDOR ({self.user_id}): Sending reply to {recipient} ---> {message[:50]}...")
        try:
            data = json.dumps({"recipient": recipient, "message": message}).encode('utf-8')
            req = urllib.request.Request(
                f"{self.base_url}/send",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    print(f"VENDOR_ERROR ({self.user_id}): Failed to send message. Status: {response.status}, Body: {response.read().decode()}")
        except Exception as e:
            print(f"VENDOR_ERROR ({self.user_id}): Exception while sending message: {e}")
