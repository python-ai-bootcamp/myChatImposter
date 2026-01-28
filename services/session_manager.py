import asyncio
import logging
import importlib
import inspect
from typing import Optional, Callable, List, Dict, Any, Awaitable
from pymongo.collection import Collection

from config_models import UserConfiguration
from queue_manager import UserQueuesManager, Message
from chat_providers.base import BaseChatProvider

# Helper to find provider class
def _find_provider_class(module, base_class: type) -> Optional[type]:
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) and issubclass(obj, base_class) and obj is not base_class:
            return obj
    return None

class SessionManager:
    """
    Manages the core connectivity session for a user.
    Responsibilities:
    1.  Initialize and manage the Chat Provider (WhatsApp connection).
    2.  Initialize and manage the User Queues.
    3.  Dispatch incoming messages to registered Feature Handlers (Observer Pattern).
    """

    def __init__(
        self, 
        config: UserConfiguration, 
        on_session_end: Optional[Callable[[str], None]] = None, 
        queues_collection: Optional[Collection] = None, 
        main_loop = None, 
        on_status_change: Optional[Callable[[str, str], Awaitable[None]]] = None
    ):
        self.user_id = config.user_id
        self.config = config
        self.on_session_end = on_session_end
        self.main_loop = main_loop
        self.on_status_change = on_status_change
        self._queues_collection = queues_collection
        
        # Components
        self.user_queues_manager: Optional[UserQueuesManager] = None
        self.provider_instance: Optional[BaseChatProvider] = None
        
        # Feature Handlers (Subscribers)
        # Signature: async def handler(correspondent_id: str, message: Message) -> None
        self._message_handlers: List[Callable[[str, Message], Awaitable[None]]] = []
        
        # Associated Services (Lifecycle Management)
        # Objects that have start/stop methods (e.g., Ingester)
        self._associated_services: List[Any] = []
        
        # Feature Registry (Access to stateful feature services)
        self.features: Dict[str, Any] = {}

        self._initialize_components()

    def _initialize_components(self):
        """Initializes Queue Manager and Chat Provider."""
        logging.info(f"SESSION ({self.user_id}): Initializing core components...")

        # 1. Initialize Queue Manager
        chat_provider_config = self.config.configurations.chat_provider_config
        provider_name = chat_provider_config.provider_name
        
        self.user_queues_manager = UserQueuesManager(
            user_id=self.user_id,
            provider_name=provider_name,
            queue_config=self.config.configurations.queue_config,
            queues_collection=self._queues_collection,
            main_loop=self.main_loop
        )
        
        # Register self as the callback to receive messages from the Queue Manager
        # Note: QueueManager calls callback(user_id, correspondent_id, message)
        self.user_queues_manager.register_callback(self._on_queue_message)
        
        logging.info(f"SESSION ({self.user_id}): Initialized queue manager.")

        # 2. Initialize Chat Provider
        try:
            provider_module = importlib.import_module(f"chat_providers.{provider_name}")
            ProviderClass = _find_provider_class(provider_module, BaseChatProvider)
            if not ProviderClass:
                raise ImportError(f"Could not find a valid chat provider class in module 'chat_providers.{provider_name}'")
            
            provider_init_params = {
                "user_id": self.user_id,
                "config": chat_provider_config,
                "user_queues": {self.user_id: self.user_queues_manager},
                "on_session_end": self.on_session_end,
                "on_status_change": self.on_status_change,
                "main_loop": self.main_loop
            }
            
            self.provider_instance = ProviderClass(**provider_init_params)
            logging.info(f"SESSION ({self.user_id}): Initialized chat provider '{provider_name}'.")
            
        except Exception as e:
            logging.error(f"SESSION ({self.user_id}): Failed to initialize provider: {e}")
            raise RuntimeError(f"Failed to initialize provider for {self.user_id}: {e}")

    def register_message_handler(self, handler: Callable[[str, Message], Awaitable[None]]):
        """Registers a feature handler to receive incoming messages."""
        self._message_handlers.append(handler)
        logging.info(f"SESSION ({self.user_id}): Registered message handler: {handler.__name__ if hasattr(handler, '__name__') else str(handler)}")

    def register_service(self, service: Any):
        """Registers an associated service (e.g. Ingester) to be stopped when session ends."""
        self._associated_services.append(service)
        logging.info(f"SESSION ({self.user_id}): Registered associated service: {service.__class__.__name__}")

    def register_feature(self, name: str, service: Any):
        """Registers a named feature service for external access (e.g. API)."""
        self.features[name] = service
        logging.info(f"SESSION ({self.user_id}): Registered feature '{name}': {service.__class__.__name__}")

    async def _on_queue_message(self, user_id: str, correspondent_id: str, message: Message):
        """
        Callback triggered by UserQueuesManager when a new message arrives.
        Dispatches the message to all registered feature handlers.
        """
        # Skip bot messages (outgoing)
        if message.source == 'bot' or message.source == 'user_outgoing':
            return

        # Dispatch to subscribers
        for handler in self._message_handlers:
            try:
                await handler(correspondent_id, message)
            except Exception as e:
                logging.error(f"SESSION ({self.user_id}): Error in feature handler: {e}")

    async def start(self):
        """Starts the provider listener."""
        if not self.provider_instance:
            raise RuntimeError(f"Session {self.user_id} cannot start: provider not initialized.")

        logging.info(f"SESSION ({self.user_id}): Starting provider listener...")
        await self.provider_instance.start_listening()
        logging.info(f"SESSION ({self.user_id}): Session started.")

    async def stop(self, cleanup_session: bool = False):
        """Stops the provider listener and associated services."""
        logging.info(f"SESSION ({self.user_id}): Stopping session... (cleanup={cleanup_session})")
        
        # Stop associated services (LIFO order typical for shutdown)
        for service in reversed(self._associated_services):
            if hasattr(service, 'stop'):
                try:
                    logging.info(f"SESSION ({self.user_id}): Stopping service {service.__class__.__name__}...")
                    if inspect.iscoroutinefunction(service.stop):
                        await service.stop()
                    else:
                        service.stop()
                except Exception as e:
                    logging.error(f"SESSION ({self.user_id}): Error stopping service {service.__class__.__name__}: {e}")

        if self.provider_instance:
            await self.provider_instance.stop_listening(cleanup_session=cleanup_session)
            
        logging.info(f"SESSION ({self.user_id}): Session stopped.")

    async def get_status(self, heartbeat: bool = False):
        """Gets connection status from the provider."""
        if self.provider_instance and hasattr(self.provider_instance, 'get_status'):
            sig = inspect.signature(self.provider_instance.get_status)
            if 'heartbeat' in sig.parameters:
                return await self.provider_instance.get_status(heartbeat=heartbeat)
            else:
                return await self.provider_instance.get_status()
        return {"status": "unknown", "message": "Provider does not support status checks."}
