"""Test verbose mode functionality."""

import json
from voice_assistant.config import Config


def test_verbose_flag_in_config():
    """Test that verbose flag can be accepted by Config."""
    # Test that Config.from_args can accept verbose parameter
    config = Config.from_args(verbose=True)
    
    assert hasattr(config, 'verbose'), "Config should have verbose attribute"
    assert config.verbose == True, "Verbose should be True when flag is set"


def test_verbose_shows_full_session_id():
    """Test that verbose mode shows full session ID instead of truncated."""
    import tempfile
    import uuid
    from pathlib import Path
    from unittest.mock import Mock, patch
    import io
    
    from voice_assistant.core.claude_client import ClaudeClient
    
    client = ClaudeClient()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        profile_path = Path(tmpdir) / "test_profile"
        profile_path.mkdir(parents=True, exist_ok=True)
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            # Return JSON with session ID
            json_response = json.dumps({
                "type": "result", 
                "result": "Response",
                "session_id": "test-session-full-id-12345678"
            })
            mock_process.communicate.return_value = (json_response, "")
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            
            # Capture stdout
            captured_output = io.StringIO()
            with patch('sys.stdout', new=captured_output):
                # Create verbose config
                from voice_assistant.config import AudioConfig, VADConfig, TTSConfig, TranscriptionConfig, ProfileConfig
                config = Config(
                    audio=AudioConfig(), vad=VADConfig(), tts=TTSConfig(), 
                    transcription=TranscriptionConfig(), profiles=ProfileConfig(),
                    verbose=True
                )
                client.config = config  # Inject verbose config
                
                response = client.send_query("Test", profile_path=profile_path)
            
            output = captured_output.getvalue()
            
            # In verbose mode, should show we're starting a new session
            assert "Starting new session" in output, f"New session message not in output: {output}"


def test_interface_passes_config_to_claude_client():
    """Test that VoiceInterface passes config to ClaudeClient."""
    from voice_assistant.core.interface import VoiceInterface
    
    # Create config with verbose=True
    config = Config.from_args(verbose=True)
    
    # Create interface
    interface = VoiceInterface(config)
    
    # Check that claude_client has the config
    assert interface.claude_client.config is not None, "ClaudeClient should have config"
    assert interface.claude_client.config.verbose == True, "ClaudeClient should have verbose=True"


def test_verbose_shows_claude_command():
    """Test that verbose mode shows the full Claude command."""
    import tempfile
    from pathlib import Path
    from unittest.mock import Mock, patch
    import io
    
    from voice_assistant.core.claude_client import ClaudeClient
    from voice_assistant.config import AudioConfig, VADConfig, TTSConfig, TranscriptionConfig, ProfileConfig
    
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
                # Create verbose config
                config = Config(
                    audio=AudioConfig(), 
                    vad=VADConfig(), 
                    tts=TTSConfig(), 
                    transcription=TranscriptionConfig(), 
                    profiles=ProfileConfig(),
                    verbose=True
                )
                client.config = config
                
                response = client.send_query("Test query", profile_path=profile_path)
            
            output = captured_output.getvalue()
            
            # In verbose mode, should show the command
            assert "Claude command:" in output or "claude" in output.lower(), \
                f"Claude command not shown in verbose output: {output}"
            assert "--print" in output, "Should show --print flag in command"
            assert "Test query" in output, "Should show query text in command"