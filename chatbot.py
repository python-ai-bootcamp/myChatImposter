import json
import importlib
import time
import threading
from typing import Dict, Any

from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain_community.llms.fake import FakeListLLM

from queue_manager import UserQueue, Message

class ChatbotModel:
    """A wrapper for the LangChain conversation model for a single user."""
    def __init__(self, user_id: str):
        self.user_id = user_id
        # Each user gets their own independent conversation chain and memory
        self.llm = FakeListLLM(responses=[
            f"Hi, I'm the bot for {self.user_id}. How can I help?",
            "That's an interesting question. Let me think...",
            "I can answer questions and tell jokes.",
            "Why don't scientists trust atoms? Because they make up everything!",
            "Is there anything else I can help with?"
        ])
        self.memory = ConversationBufferMemory()
        self.conversation = ConversationChain(llm=self.llm, memory=self.memory, verbose=False)

    def get_response(self, message: str) -> str:
        return self.conversation.predict(input=message)

class Orchestrator:
    """Manages all users, queues, vendors, and chatbot models."""
    def __init__(self, config_path: str):
        self.user_configs = self._load_config(config_path)

        self.user_queues: Dict[str, UserQueue] = {}
        self.chatbot_models: Dict[str, ChatbotModel] = {}
        self.vendor_instances: Dict[str, Any] = {}

    def _load_config(self, path: str) -> list:
        print(f"ORCHESTRATOR: Loading configuration from {path}...")
        with open(path) as f:
            return json.load(f)

    def _initialize_components(self):
        print("ORCHESTRATOR: Initializing components for all users...")
        # 1. Initialize queues for all users first
        for config in self.user_configs:
            user_id = config['user_id']
            q_config = config['queue_config']
            self.user_queues[user_id] = UserQueue(
                user_id=user_id,
                max_messages=q_config['max_messages'],
                max_characters=q_config['max_characters'],
                max_days=q_config['max_days']
            )
            print(f"ORCHESTRATOR: Initialized queue for {user_id}.")

        # 2. Initialize chatbot models and vendors for each user
        for config in self.user_configs:
            user_id = config['user_id']

            # Initialize the chatbot model
            self.chatbot_models[user_id] = ChatbotModel(user_id)
            print(f"ORCHESTRATOR: Initialized chatbot model for {user_id}.")

            # EXTENSIBILITY POINT: Dynamically load and initialize the vendor.
            # This allows adding new communication platforms without changing this core file.
            # It works by loading the module from the `vendor/` directory that matches
            # the `vendor_name` specified in the user's configuration.
            vendor_name = config['vendor_name']
            vendor_module = importlib.import_module(f"vendor.{vendor_name}")

            # TODO: Future improvement: The class name is currently hardcoded.
            # A better approach would be to have a naming convention (e.g., Vendor)
            # or specify the class name in the configuration file.
            VendorClass = getattr(vendor_module, 'DummyVendor') # Assuming class name is consistent

            # Each vendor is initialized with its own config and gets access to the
            # dictionary of all user queues, although it should only use its own.
            self.vendor_instances[user_id] = VendorClass(
                user_id=user_id,
                config=config['vendor_config'],
                user_queues=self.user_queues
            )
            print(f"ORCHESTRATOR: Initialized vendor '{vendor_name}' for {user_id}.")

    def _message_callback(self, message: Message):
        """
        The central callback that processes a new message from any queue.
        This method is the lynchpin connecting the vendor (input) to the
        chatbot (processing) and back to the vendor (output).
        """
        print(f"ORCHESTRATOR: Callback received for message {message.id} from {message.sendingUser}.")

        # We only process messages from users, not from the bot itself.
        # The bot's own responses are added to the queue for history, but should not trigger a response.
        if message.sendingUser.startswith("bot_"):
            return

        user_id = message.sendingUser
        chatbot = self.chatbot_models.get(user_id)
        vendor = self.vendor_instances.get(user_id)

        if not chatbot or not vendor:
            print(f"ORCHESTRATOR_ERROR: No chatbot or vendor for user {user_id}.")
            return

        # Get a response from the LLM
        response_text = chatbot.get_response(message.content)

        # Send the response back through the vendor
        vendor.sendMessage(response_text)

        # Add the bot's response to the queue for a complete history
        bot_user_id = f"bot_{user_id}"
        user_queue = self.user_queues.get(user_id)
        if user_queue:
            user_queue.add_message(content=response_text, sending_user=bot_user_id)

    def start(self):
        """Initializes, wires up, and starts the whole system."""
        self._initialize_components()

        print("\nORCHESTRATOR: Registering callbacks and starting vendor listeners...")
        for user_id, queue in self.user_queues.items():
            queue.register_callback(self._message_callback)
            print(f"ORCHESTRATOR: Registered callback for {user_id}'s queue.")

        for user_id, vendor in self.vendor_instances.items():
            vendor.start_listening()

        print("\nORCHESTRATOR: System is running. Main thread will wait for vendors to complete...")

        # Collect all vendor threads to wait for them
        threads = []
        for vendor in self.vendor_instances.values():
            if vendor.thread and vendor.thread.is_alive():
                threads.append(vendor.thread)

        # Wait for all threads to complete their execution
        for thread in threads:
            thread.join()

        print("\nORCHESTRATOR: All vendor simulations have finished. System shutting down.")

if __name__ == "__main__":
    orchestrator = Orchestrator(config_path='configurations/users.json')
    orchestrator.start()
