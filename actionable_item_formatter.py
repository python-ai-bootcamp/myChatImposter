
import io
import uuid
import datetime
from typing import Dict, List, Optional
from email.utils import formatdate

class ActionableItemFormatter:
    """
    Formatter for Actionable Items.
    Handles localization (English/Hebrew) and formatting for WhatsApp "Visual Cards".
    Also generates .ics calendar files.
    """

    STRINGS = {
        "en": {
            "header_icon": "📝",
            "divider": "─────────────────────",
            "group": "📂 *Group*",
            "goal": "📌 *Description*",
            "deadline_text": "⏰ *Due (from text)*",
            "deadline_date": "🗓️ *Date*",
            "context_header": "💬 *Relevant Messages*",
            "footer": "Attached: 📎 Calendar Event"
        },
        "he": {
            "header_icon": "📝",
            "divider": "─────────────────────",
            "group": "📂 *קבוצה*",
            "goal": "📌 *תיאור*",
            "deadline_text": "⏰ *מועד (ממקור הטקסט)*",
            "deadline_date": "🗓️ *תאריך יעד*",
            "context_header": "💬 *הודעות רלוונטיות*",
            "footer": "מצורף: 📎 אירוע ליומן"
        }
    }

    @staticmethod
    def _get_strings(language_code: str):
        return ActionableItemFormatter.STRINGS.get(language_code, ActionableItemFormatter.STRINGS["en"])

    @staticmethod
    def format_card(item: Dict, language_code: str = "en") -> str:
        """
        Formats an actionable item as a Visual Card.
        """
        s = ActionableItemFormatter._get_strings(language_code)
        
        # Extract fields
        title = item.get("task_title", "Untitled Task")
        group_name = item.get("group_display_name", "")
        description = item.get("task_description", "")
        text_deadline = item.get("text_deadline", "")
        timestamp_deadline = item.get("timestamp_deadline", "")
        messages = item.get("relevant_task_messages", [])

        # Build Message
        lines = []
        lines.append(f"{s['header_icon']} *{title}*")
        lines.append(s['divider'])

        if group_name:
            lines.append("")
            lines.append(f"{s['group']}: {group_name}")
        
        if description:
            lines.append("")
            lines.append(f"{s['goal']}: {description}")
        
        if text_deadline:
            lines.append("")
            lines.append(f"{s['deadline_text']}: {text_deadline}")
            
        if timestamp_deadline:
            # Try to format timestamp nicely if it is standard string
            # Input format from LLM is usually "YYYY-MM-DD HH:MM:SS"
            # We can leave it as is or format it. Let's leave as is for robustness.
            lines.append("")
            lines.append(f"{s['deadline_date']}: {timestamp_deadline}")
            
        lines.append("") # Empty line

        # Add Context / Messages
        if messages:
            lines.append(s['context_header'])
            for msg in messages:
                sender = msg.get("sender", "Unknown")
                content = msg.get("content", "")
                # Quote the content
                lines.append(f"> \"_{content}_\"")
                # Attribute to sender at the bottom (per user request)
                lines.append(f"> — {sender}")
                lines.append("") # Spacing between messages

        # Footer
        # lines.append(s['footer']) 

        return "\n".join(lines)

    @staticmethod
    def generate_ics(item: Dict) -> bytes:
        """
        Generates an iCalendar (.ics) file content as bytes.
        """
        title = item.get("task_title", "Actionable Item")
        description = item.get("task_description", "")
        deadline_str = item.get("timestamp_deadline", "") # Expected: YYYY-MM-DD HH:MM:SS
        
        # Parse start time (Deadline)
        try:
            dt_end = datetime.datetime.strptime(deadline_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Fallback if parsing fails: Use now + 1 hour, or just today.
            dt_end = datetime.datetime.now() + datetime.timedelta(hours=24)

        # For the calendar event, let's make it a 1-hour block ending at the deadline
        # Or just a point in time? Usually tasks are points or deadlines.
        # Let's start 1 hour before deadline.
        dt_start = dt_end - datetime.timedelta(hours=1)

        # Format for ICS (UTC)
        # We assume the timestamp provided by LLM is in the user's local time (conceptually).
        # ICS requires specific formatting. Simple format: YYYYMMDDTHHmmSS
        
        def format_dt(dt):
            return dt.strftime("%Y%m%dT%H%M%S")

        created_dt = format_dt(datetime.datetime.now())
        start_str = format_dt(dt_start)
        end_str = format_dt(dt_end)
        uid = f"{uuid.uuid4()}@mychatimposter.com"

        # Escape special characters in description (newlines, commas, semicolons)
        safe_desc = description.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
        safe_title = title.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

        ics_content = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MyChatImposter//ActionableQueue//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{created_dt}",
            f"DTSTART:{start_str}",
            f"DTEND:{end_str}",
            f"SUMMARY:{safe_title}",
            f"DESCRIPTION:{safe_desc}",
            "STATUS:CONFIRMED",
            "END:VEVENT",
            "END:VCALENDAR"
        ]
        
        return "\n".join(ics_content).encode('utf-8')

