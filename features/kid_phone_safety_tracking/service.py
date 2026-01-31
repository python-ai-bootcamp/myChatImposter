import logging
from queue_manager import Message
from services.session_manager import SessionManager

class KidPhoneSafetyService:
    """
    Service that subscribers to incoming messages and performs safety checks.
    """
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.user_id = session_manager.config.user_id

    async def handle_message(self, correspondent_id: str, message: Message):
        """
        Handles kid phone safety tracking.
        """
        if not self.session_manager.config.features.kid_phone_safety_tracking.enabled:
            return

        logging.info(f"KID_SAFETY ({self.user_id}): Handling live message for safety check.")
