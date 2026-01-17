"""
LLM Recorder - Records LLM prompts and responses to files for evaluation.

File structure:
./log/llm_recordings/<USER_ID>/<FEATURE_NAME>/<CORRESPONDENT_ID>/<EPOCH>_prompt.txt
./log/llm_recordings/<USER_ID>/<FEATURE_NAME>/<CORRESPONDENT_ID>/<EPOCH>_response.txt
"""

from pathlib import Path
from typing import Optional, List
import time


class LLMRecorder:
    """Records LLM prompts and responses to files for later evaluation."""
    
    def __init__(self, user_id: str, feature_name: str, correspondent_id: str):
        """
        Initialize the recorder.
        
        Args:
            user_id: The user identifier
            feature_name: The feature using the LLM (e.g., "periodic_group_tracking", "automatic_bot_reply")
            correspondent_id: The correspondent/group identifier
        """
        self.user_id = user_id
        self.feature_name = feature_name
        self.correspondent_id = self._sanitize_path(correspondent_id)
        self.base_path = Path("./log/llm_recordings")
        self._epoch_ts: Optional[int] = None
    
    def _sanitize_path(self, path_component: str) -> str:
        """Sanitize path component to be filesystem-safe."""
        # Replace characters that are problematic in file paths
        return path_component.replace(":", "_").replace("/", "_").replace("\\", "_")
    
    def get_recording_dir(self) -> Path:
        """Get the directory for recordings."""
        return self.base_path / self.user_id / self.feature_name / self.correspondent_id
    
    def start_recording(self) -> int:
        """Start a new recording session and return the epoch timestamp."""
        self._epoch_ts = int(time.time())
        return self._epoch_ts
    
    def record_prompt(self, system_prompt: str, user_input: str, history: Optional[List] = None, epoch_ts: Optional[int] = None):
        """
        Write the full prompt to <epoch>_prompt.txt
        
        Args:
            system_prompt: The system prompt sent to the LLM
            user_input: The user input/message sent to the LLM
            history: Optional conversation history
            epoch_ts: Optional epoch timestamp (uses current session if not provided)
        """
        ts = epoch_ts or self._epoch_ts
        if ts is None:
            ts = self.start_recording()
        
        path = self.get_recording_dir() / f"{ts}_prompt.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        content = f"=== SYSTEM PROMPT ===\n{system_prompt}\n\n"
        if history:
            content += f"=== HISTORY ===\n{history}\n\n"
        content += f"=== USER INPUT ===\n{user_input}"
        
        path.write_text(content, encoding='utf-8')
    
    def record_response(self, response: str, epoch_ts: Optional[int] = None):
        """
        Write the response to <epoch>_response.txt
        
        Args:
            response: The LLM response
            epoch_ts: Optional epoch timestamp (uses current session if not provided)
        """
        ts = epoch_ts or self._epoch_ts
        if ts is None:
            raise ValueError("No epoch timestamp available. Call start_recording() or provide epoch_ts.")
        
        path = self.get_recording_dir() / f"{ts}_response.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        
        path.write_text(response, encoding='utf-8')
