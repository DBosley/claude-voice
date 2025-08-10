"""Tests for Claude client."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from voice_assistant.core import ClaudeClient


class TestClaudeClient:
    """Test Claude CLI client functionality."""
    
    @pytest.fixture
    def client(self):
        """Create Claude client."""
        return ClaudeClient()
    
    def test_initialization(self, client):
        """Test client initialization."""
        assert client.current_process is None
        assert client.is_processing == False
    
    @patch('subprocess.Popen')
    def test_send_query(self, mock_popen, client):
        """Test sending query to Claude."""
        # Mock successful response
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Test response", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        response = client.send_query("Test query")
        
        assert response == "Test response"
        mock_popen.assert_called_once()
        
        # Check command
        cmd = mock_popen.call_args[0][0]
        assert cmd[0] == "claude"
        assert "Test query" in cmd
    
    @patch('subprocess.Popen')
    def test_send_query_with_profile(self, mock_popen, client):
        """Test sending query with profile context."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Profile response", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # Use a temp directory for profile
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "test_profile"
            profile_path.mkdir(parents=True, exist_ok=True)
            
            response = client.send_query("Test query", profile_path=profile_path)
            
            assert response == "Profile response"
            
            # Check command format (first query should not have --resume)
            cmd = mock_popen.call_args[0][0]
            # First query doesn't use --session-id or --resume
            assert "--session-id" not in cmd, "Should not use --session-id"
            # Check working directory is set to profile path
            kwargs = mock_popen.call_args[1]
            assert kwargs['cwd'] == str(profile_path)
    
    @patch('subprocess.Popen')
    def test_send_query_with_reset(self, mock_popen, client):
        """Test sending query with context reset."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("Reset response", "")
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        
        # Use a temp directory for profile
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "test_profile"
            profile_path.mkdir(parents=True, exist_ok=True)
            
            response = client.send_query(
                "Test query",
                profile_path=profile_path,
                reset_context=True
            )
            
            assert response == "Reset response"
            
            # Check command doesn't include profile when resetting
            cmd = mock_popen.call_args[0][0]
            assert "-c" not in cmd
    
    @patch('subprocess.Popen')
    def test_send_query_error(self, mock_popen, client):
        """Test query error handling."""
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("", "Error message")
        mock_process.returncode = 1
        mock_popen.return_value = mock_process
        
        response = client.send_query("Test query")
        
        assert "Error:" in response
        assert "Error message" in response
    
    @patch('subprocess.Popen')
    def test_cancel(self, mock_popen, client):
        """Test cancelling current process."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        
        # Start a process
        client.current_process = mock_process
        
        # Cancel it
        client.cancel()
        
        mock_process.terminate.assert_called_once()
        assert client.current_process is None
    
    def test_is_processing_property(self, client):
        """Test is_processing property."""
        assert client.is_processing == False
        
        client.current_process = MagicMock()
        assert client.is_processing == True
        
        client.current_process = None
        assert client.is_processing == False