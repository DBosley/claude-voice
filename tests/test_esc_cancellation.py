"""Test ESC key cancellation handling."""

import sys
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestESCCancellation:
    """Test that ESC properly cancels operations."""
    
    def test_esc_during_claude_processing_terminates_cleanly(self):
        """Test that pressing ESC during Claude processing terminates cleanly."""
        from voice_assistant.core.claude_client import ClaudeClient
        
        client = ClaudeClient()
        
        # Mock subprocess
        mock_process = Mock()
        mock_process.poll.return_value = None  # Process still running
        mock_process.returncode = None
        
        # Simulate that terminate is called
        def mock_terminate():
            mock_process.poll.return_value = -15  # SIGTERM
            mock_process.returncode = -15
        
        mock_process.terminate = mock_terminate
        mock_process.kill = Mock()
        
        client.current_process = mock_process
        
        # Call cancel
        client.cancel()
        
        # Should have called terminate
        assert mock_process.terminate.called or mock_process.kill.called
        
        # Process should be None after cancel
        assert client.current_process is None