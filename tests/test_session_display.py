"""Test session ID display functionality."""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch
import io
import sys

from voice_assistant.core.claude_client import ClaudeClient


def test_displays_session_id_on_new_session():
    """Test that session ID is displayed when creating a new session."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = ("Response", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Capture stdout
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                response = client.send_query("Test", profile_path=profile_path)
            
            output = captured_output.getvalue()
            
            # Should display session creation message with ID
            assert "Starting new session" in output or "Creating session" in output, \
                f"No session creation message in output: {output}"
            
            # Should show at least first 8 chars of session ID
            session_file = profile_path / ".session_id"
            if session_file.exists():
                session_id = session_file.read_text().strip()
                assert session_id[:8] in output, \
                    f"Session ID prefix {session_id[:8]} not shown in output: {output}"


def test_displays_session_id_on_resume():
    """Test that session ID is displayed when resuming an existing session."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Create existing session file
        existing_session_id = str(uuid.uuid4())
        session_file = profile_path / ".session_id"
        session_file.write_text(existing_session_id)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = ("Response", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Capture stdout
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                response = client.send_query("Test", profile_path=profile_path)
            
            output = captured_output.getvalue()
            
            # Should display session resume message with ID
            assert "Resuming session" in output or "Resume session" in output, \
                f"No session resume message in output: {output}"
            
            # Should show at least first 8 chars of session ID
            assert existing_session_id[:8] in output, \
                f"Session ID prefix {existing_session_id[:8]} not shown in output: {output}"