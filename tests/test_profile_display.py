"""Test profile name display in interface modes."""

import io
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from voice_assistant.config import Config
from voice_assistant.core.interface import VoiceInterface


def test_wake_word_mode_shows_profile_when_loaded():
    """Test that wake word mode displays the current profile name."""
    config = Config.default()
    interface = VoiceInterface(config)
    
    # Set a current profile
    interface.profile_manager.current_profile = "test_profile"
    
    # Capture stdout
    captured_output = io.StringIO()
    
    # Mock detect_wake_word to return False (no activation)
    with patch.object(interface, 'detect_wake_word', return_value=False):
        # Use a side effect to stop the loop after one iteration
        with patch('time.sleep', side_effect=KeyboardInterrupt):
            with patch('sys.stdout', new=captured_output):
                try:
                    interface.wake_word_mode()
                except KeyboardInterrupt:
                    pass
    
    output = captured_output.getvalue()
    assert "Current profile: test_profile" in output, f"Profile not shown in output: {output}"


def test_conversation_mode_shows_profile():
    """Test that conversation mode displays and speaks the current profile."""
    config = Config.default()
    interface = VoiceInterface(config)
    
    # Set a current profile
    interface.profile_manager.current_profile = "conversation_profile"
    
    # Mock listen to return goodbye immediately
    with patch.object(interface, 'listen', return_value="goodbye"):
        # Mock speak to capture what was spoken
        with patch.object(interface, 'speak') as mock_speak:
            # Capture stdout
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                interface.conversation_mode()
    
    output = captured_output.getvalue()
    
    # Check that profile was printed
    assert "Current profile: conversation_profile" in output, f"Profile not shown in output: {output}"
    
    # Check that profile was spoken
    speak_calls = [str(call) for call in mock_speak.call_args_list]
    assert any("Using profile: conversation_profile" in str(call) for call in speak_calls), \
        f"Profile not spoken. Calls: {speak_calls}"


def test_single_question_mode_shows_profile():
    """Test that single question mode displays the current profile."""
    config = Config.default()
    interface = VoiceInterface(config)
    
    # Set a current profile  
    interface.profile_manager.current_profile = "question_profile"
    
    # Mock listen to return None
    with patch.object(interface, 'listen', return_value=None):
        # Mock speak
        with patch.object(interface, 'speak'):
            # Capture stdout
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                interface.single_question_mode()
    
    output = captured_output.getvalue()
    assert "Current profile: question_profile" in output, f"Profile not shown in output: {output}"