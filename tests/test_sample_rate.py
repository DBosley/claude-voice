"""Tests for sample rate configuration."""

import subprocess
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.config import Config


class TestSampleRateConfiguration:
    """Test sample rate configuration options."""

    def test_sample_rate_from_cli_argument(self):
        """Test that sample rate can be set via CLI argument."""
        config = Config.from_args(sample_rate=48000)
        assert config.audio.sample_rate == 48000

    def test_cli_accepts_sample_rate_argument(self):
        """Test that the CLI script accepts --sample-rate argument."""
        result = subprocess.run(
            [sys.executable, "claude_voice.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert "--sample-rate" in result.stdout
        assert "16000" in result.stdout
        assert "48000" in result.stdout

    def test_cli_passes_sample_rate_to_config(self):
        """Test that CLI passes sample rate to Config correctly."""
        # This test verifies the integration by checking that
        # the sample_rate parameter gets passed through
        from unittest.mock import patch
        import claude_voice
        
        with patch("claude_voice.VoiceInterface") as mock_interface:
            with patch("sys.argv", ["claude_voice.py", "wake", "--sample-rate", "48000"]):
                # Capture the config that gets created
                original_from_args = Config.from_args
                captured_kwargs = {}
                
                def capture_from_args(**kwargs):
                    captured_kwargs.update(kwargs)
                    return original_from_args(**kwargs)
                
                with patch.object(Config, "from_args", side_effect=capture_from_args):
                    try:
                        claude_voice.main()
                    except SystemExit:
                        pass  # Expected if interface.run() is mocked
                
                # Verify sample_rate was passed
                assert "sample_rate" in captured_kwargs
                assert captured_kwargs["sample_rate"] == 48000