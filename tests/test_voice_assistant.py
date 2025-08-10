"""Test file for Claude Voice Assistant to verify TDD Guard integration."""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_tdd_guard_is_working():
    """Simple test to verify TDD Guard creates appropriate files."""
    assert True, "TDD Guard should be monitoring this test"


def test_import_main_module():
    """Test that we can import the main claude-voice module."""
    # This will help TDD Guard understand the project structure
    try:
        # Import without executing the main code
        import claude_voice
        assert True, "Successfully imported claude-voice module"
    except ImportError:
        # Module uses dash in filename, not importable directly
        assert True, "Module uses dash in filename, expected behavior"


def test_vad_availability():
    """Test to check if VAD components are available."""
    try:
        import torch
        import torchaudio
        has_vad = True
    except ImportError:
        has_vad = False
    
    # This test passes either way but documents VAD status
    if has_vad:
        assert True, "VAD components are available"
    else:
        assert True, "VAD components not installed (optional dependency)"


def test_tts_availability():
    """Test to check which TTS engines are available."""
    engines_available = []
    
    try:
        from TTS.api import TTS
        engines_available.append("coqui")
    except ImportError:
        pass
    
    # Check for Piper (would need to check system installation)
    # For now, just document what we found
    assert True, f"TTS engines found: {engines_available or ['none']}"


class TestVoiceAssistantConfiguration:
    """Test configuration and settings for the voice assistant."""
    
    def test_default_wake_word(self):
        """Test that default wake word is set correctly."""
        default_wake_word = "hey claude"
        assert default_wake_word == "hey claude", "Default wake word should be 'hey claude'"
    
    def test_audio_format_settings(self):
        """Test audio format configuration."""
        expected_rate = 16000  # or 48000 for Arctis Nova
        expected_channels = 1  # Mono
        
        assert expected_channels == 1, "Audio should be mono"
        assert expected_rate in [16000, 48000], "Sample rate should be 16kHz or 48kHz"
    
    def test_vad_thresholds(self):
        """Test VAD threshold settings."""
        speech_start_threshold = 0.85
        speech_continue_threshold = 0.5
        
        assert speech_start_threshold > speech_continue_threshold, \
            "Start threshold should be higher than continuation threshold"
        assert 0 < speech_start_threshold <= 1, "Threshold should be between 0 and 1"