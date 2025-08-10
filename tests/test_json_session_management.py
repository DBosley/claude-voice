"""Test JSON-based session management."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from voice_assistant.core.claude_client import ClaudeClient


def test_uses_json_output_format():
    """Test that Claude client uses JSON output format."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            # Simulate JSON response from Claude
            json_response = json.dumps({
                "type": "result",
                "result": "Test response",
                "session_id": "test-session-123"
            })
            mock_process.communicate.return_value = (json_response, "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            response = client.send_query("Test", profile_path=profile_path)
            
            # Check that --output-format json was used
            cmd = mock_popen.call_args[0][0]
            assert "--output-format" in cmd, f"--output-format not in command: {cmd}"
            assert "json" in cmd, f"json format not specified: {cmd}"
            
            # Check that response was extracted from JSON
            assert response == "Test response", f"Expected 'Test response' but got {response}"


def test_updates_session_id_from_response():
    """Test that session ID is updated from Claude's response."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            # First response with session ID
            json_response = json.dumps({
                "type": "result",
                "result": "First response",
                "session_id": "new-session-456"
            })
            mock_process.communicate.return_value = (json_response, "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # First query
            response = client.send_query("First query", profile_path=profile_path)
            
            # Check that session file was updated with new ID
            session_file = profile_path / ".session_id"
            assert session_file.exists(), "Session file should exist"
            saved_session_id = session_file.read_text().strip()
            assert saved_session_id == "new-session-456", f"Expected 'new-session-456' but got {saved_session_id}"