
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from actionable_item_formatter import ActionableItemFormatter

def test_ics_generation():
    item = {
        "task_title": "Test Task",
        "task_description": "This is a test task description.",
        "timestamp_deadline": "2026-02-20 12:00:00",
        "group_display_name": "Test Group"
    }

    try:
        ics_bytes = ActionableItemFormatter.generate_ics(item)
        print(f"ICS Bytes Length: {len(ics_bytes)}")
        print("--- Content ---")
        print(ics_bytes.decode('utf-8'))
        print("--- End Content ---")
        
        if len(ics_bytes) == 0:
            print("ERROR: Generated ICS is empty!")
            sys.exit(1)
            
    except Exception as e:
        print(f"Exception during generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_ics_generation()
