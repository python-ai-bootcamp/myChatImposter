from message_processors.base import BaseMessageProcessor

class TextMessageProcessor(BaseMessageProcessor):
    async def process(self, message_doc: dict, target_instance) -> None:
        content = message_doc.get("content")
        recipient_jid = target_instance.provider_instance.user_jid
        
        text_content = str(content)
        await target_instance.provider_instance.sendMessage(
            recipient=recipient_jid,
            message=text_content
        )
