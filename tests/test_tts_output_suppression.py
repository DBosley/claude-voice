"""Test that TTS engines suppress verbose output."""

import sys
import io
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTTSOutputSuppression:
    """Test that TTS engines don't pollute stdout/stderr."""
    
    def test_coqui_tts_suppresses_verbose_output(self):
        """Test that CoquiTTS doesn't print debug messages during generation."""
        from voice_assistant.tts.coqui import CoquiTTS
        
        # Mock the TTS model
        with patch('voice_assistant.tts.coqui.TTS') as mock_tts_class:
            mock_model = Mock()
            mock_tts_class.return_value = mock_model
            
            # Make the model print something (simulating Coqui's verbose output)
            def verbose_tts_to_file(**kwargs):
                print(" > Text splitted to sentences.")
                print(" > Processing time: 0.5")
                sys.stderr.write(" > Real-time factor: 0.3\n")
            
            mock_model.tts_to_file = verbose_tts_to_file
            
            # Create TTS engine
            tts = CoquiTTS(voice="british_male", speech_rate=1.0)
            tts.model = mock_model
            
            # Capture output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            captured_stdout = io.StringIO()
            captured_stderr = io.StringIO()
            sys.stdout = captured_stdout
            sys.stderr = captured_stderr
            
            try:
                # Generate audio (should suppress output)
                tts._generate_audio("Hello world", friendly=False)
                
                # Check that nothing was printed
                stdout_content = captured_stdout.getvalue()
                stderr_content = captured_stderr.getvalue()
                
                assert "Text splitted" not in stdout_content, "Coqui debug output leaked to stdout"
                assert "Processing time" not in stdout_content, "Coqui debug output leaked to stdout"
                assert "Real-time factor" not in stderr_content, "Coqui debug output leaked to stderr"
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr