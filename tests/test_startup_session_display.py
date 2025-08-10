"""Test session status display at startup."""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch
import io

from voice_assistant.config import Config
from voice_assistant.core.interface import VoiceInterface


def test_shows_existing_session_at_startup():
    """Test that existing session is shown when starting wake word mode."""
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Create a session file in the context directory
            context_dir = Path(".context")
            context_dir.mkdir(parents=True, exist_ok=True)
            
            # Create existing session file
            existing_session_id = str(uuid.uuid4())
            session_file = context_dir / ".session_id"
            session_file.write_text(existing_session_id)
            
            # Now create interface
            config = Config.default()
            interface = VoiceInterface(config)
            
            # Capture stdout
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                # Call check_session_status
                interface.check_session_status()
            
            output = captured_output.getvalue()
            
            # Should show existing session info
            assert "Existing session" in output or "session found" in output.lower(), \
                f"No session info shown at startup: {output}"
            assert existing_session_id[:8] in output, \
                f"Session ID {existing_session_id[:8]} not shown: {output}"
        finally:
            os.chdir(original_cwd)


def test_wake_word_mode_shows_session_status():
    """Test that wake word mode displays session status at startup."""
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            # Create a session file in the context directory
            context_dir = Path(".context")
            context_dir.mkdir(parents=True, exist_ok=True)
            
            # Create existing session file
            existing_session_id = str(uuid.uuid4())
            session_file = context_dir / ".session_id"
            session_file.write_text(existing_session_id)
            
            # Now create interface
            config = Config.default()
            interface = VoiceInterface(config)
            
            # Capture stdout
            captured_output = io.StringIO()
            
            # Mock detect_wake_word to return False
            with patch.object(interface, 'detect_wake_word', return_value=False):
                # Use a side effect to stop the loop after one iteration
                with patch('time.sleep', side_effect=KeyboardInterrupt):
                    with patch('sys.stdout', new=captured_output):
                        try:
                            interface.wake_word_mode()
                        except KeyboardInterrupt:
                            pass
            
            output = captured_output.getvalue()
            
            # Should show existing session info
            assert "Existing session" in output or "session found" in output.lower(), \
                f"No session info shown in wake word mode: {output}"
            assert existing_session_id[:8] in output, \
                f"Session ID {existing_session_id[:8]} not shown: {output}"
        finally:
            os.chdir(original_cwd)