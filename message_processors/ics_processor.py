from message_processors.base import BaseMessageProcessor
from actionable_item_formatter import ActionableItemFormatter

class IcsActionableItemProcessor(BaseMessageProcessor):
    async def process(self, message_doc: dict, target_instance) -> None:
        content = message_doc.get("content")
        # Backwards compatibility: if content missing, look for actionable_item
        if content is None:
            content = message_doc.get("actionable_item")
            
        actionable_item = content
        recipient_jid = target_instance.provider_instance.user_jid
        message_id = str(message_doc.get("_id"))

        # Determine language code
        language_code = "en" # Default
        if target_instance.config and target_instance.config.configurations and target_instance.config.configurations.user_details:
             language_code = target_instance.config.configurations.user_details.language_code

        # 1. Format the Visual Card (Text)
        formatted_text = ActionableItemFormatter.format_card(actionable_item, language_code)
        
        # 2. Generate Calendar Event
        ics_bytes = ActionableItemFormatter.generate_ics(actionable_item)
        ics_filename = f"task_{message_id[:8]}.ics"
        
        # 3. Send as Single Message (File + Caption)
        await target_instance.provider_instance.send_file(
            recipient=recipient_jid,
            file_data=ics_bytes,
            filename=ics_filename,
            mime_type="text/calendar",
            caption=formatted_text
        )
