"""Tests for goodbye detection in different modes."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.config import Config


class TestGoodbyeDetection:
    """Test that goodbye properly exits in all modes."""

    def test_conversation_mode_detects_goodbye_variations(self):
        """Test that conversation mode properly detects goodbye variations."""
        from voice_assistant.core.interface import VoiceInterface
        
        goodbye_variations = [
            "goodbye",
            "Goodbye",
            "GOODBYE",
            "goodbye.",
            "Goodbye!",
            "goodbye?",
            "exit",
            "Exit",
            "quit",
            "Quit"
        ]
        
        for text in goodbye_variations:
            # Check if the text is detected as a goodbye
            result = VoiceInterface._is_goodbye_command(text)
            assert result is True, f"Failed to detect '{text}' as goodbye"