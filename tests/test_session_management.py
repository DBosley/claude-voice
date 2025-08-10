"""Test session management with Claude CLI."""

import tempfile
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from voice_assistant.core.claude_client import ClaudeClient


def test_uses_print_mode():
    """Test that --print flag is always used for non-interactive mode."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = ("Response", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Send query
            response = client.send_query("Test", profile_path=profile_path)
            
            # Check that --print was used
            cmd = mock_popen.call_args[0][0]
            assert "--print" in cmd, f"--print not found in command: {cmd}"


def test_creates_new_session_on_first_query():
    """Test that a new session ID is created for first query."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = ("Response", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Send first query
            response = client.send_query("Hello", profile_path=profile_path)
            
            # Check that --session-id was NOT used (we let Claude generate it)
            cmd = mock_popen.call_args[0][0]
            assert "--session-id" not in cmd, f"--session-id should not be in command: {cmd}"
            assert "--resume" not in cmd, f"--resume should not be in command for new session: {cmd}"
            
            # Session file creation now happens after response
            # So we don't check for it here


def test_resumes_existing_session():
    """Test that existing session is resumed."""
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
            
            # Send query
            response = client.send_query("Hello again", profile_path=profile_path)
            
            # Check that --resume was used with existing session ID
            cmd = mock_popen.call_args[0][0]
            assert "--resume" in cmd, f"--resume not found in command: {cmd}"
            assert existing_session_id in cmd, f"Session ID {existing_session_id} not in command: {cmd}"


def test_reset_context_creates_new_session():
    """Test that reset_context creates a new session."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        # Create existing session file
        old_session_id = str(uuid.uuid4())
        session_file = profile_path / ".session_id"
        session_file.write_text(old_session_id)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.communicate.return_value = ("Response", "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Send query with reset_context
            response = client.send_query(
                "Fresh start", 
                profile_path=profile_path,
                reset_context=True
            )
            
            # Check that --resume was NOT used when resetting
            cmd = mock_popen.call_args[0][0]
            assert "--resume" not in cmd, f"--resume should not be in command when resetting: {cmd}"
            
            # Session file should be deleted after reset
            assert not session_file.exists(), f"Session file should be deleted after reset"


def test_creates_session_without_profile():
    """Test that session management works when no profile is provided."""
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temp directory to avoid polluting project
        import os
        original_cwd = os.getcwd()
        os.chdir(tmpdir)
        
        try:
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.communicate.return_value = ("Response", "")
                mock_process.returncode = 0
                mock_popen.return_value = mock_process
                
                # Send query without profile
                response = client.send_query("Hello")
                
                # Check that --session-id was NOT used (we let Claude generate it)
                cmd = mock_popen.call_args[0][0]
                assert "--session-id" not in cmd, f"--session-id should not be in command: {cmd}"
                assert "--resume" not in cmd, f"--resume should not be in command for new session: {cmd}"
        finally:
            os.chdir(original_cwd)