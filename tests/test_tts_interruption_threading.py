"""Tests for TTS interruption with threading (real-world behavior)."""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from voice_assistant.core.interface import VoiceInterface
from voice_assistant.config import Config, AudioConfig, VADConfig, TTSConfig, TranscriptionConfig, ProfileConfig


class TestTTSInterruptionThreading:
    """Test TTS interruption with proper threading for real-world usage."""
    
    @pytest.fixture
    def interface(self):
        """Create a VoiceInterface instance with real components."""
        config = Config(
            audio=AudioConfig(),
            vad=VADConfig(),
            tts=TTSConfig(engine="coqui"),
            transcription=TranscriptionConfig(),
            profiles=ProfileConfig()
        )
        interface = VoiceInterface(config)
        
        # Mock only the TTS engine to control playback
        interface.tts_engine = Mock()
        interface.tts_engine.is_speaking = True
        interface.tts_engine.stop = Mock()
        
        # Simulate TTS speaking for 3 seconds
        def simulate_speak(text, friendly=False):
            interface.tts_engine.is_speaking = True
            for _ in range(30):  # 3 seconds in 0.1s intervals
                if not interface.tts_engine.is_speaking:
                    break
                time.sleep(0.1)
            interface.tts_engine.is_speaking = False
        
        interface.tts_engine.speak = Mock(side_effect=simulate_speak)
        return interface
    
    def test_esc_interrupts_during_playback(self, interface):
        """Test that ESC key can interrupt TTS mid-playback."""
        with patch('sys.stdin') as mock_stdin:
            with patch('select.select') as mock_select:
                with patch('tty.setraw'):
                    with patch('termios.tcgetattr'):
                        with patch('termios.tcsetattr'):
                            # Simulate ESC pressed after 0.5 seconds
                            def delayed_esc(*args, **kwargs):
                                # First few calls: no input
                                if not hasattr(delayed_esc, 'count'):
                                    delayed_esc.count = 0
                                delayed_esc.count += 1
                                
                                if delayed_esc.count < 5:  # First 0.5 seconds
                                    return ([], [], [])
                                else:  # ESC available
                                    return ([mock_stdin], [], [])
                            
                            mock_select.side_effect = delayed_esc
                            mock_stdin.read.return_value = '\x1b'  # ESC key
                            
                            start_time = time.time()
                            interface.speak("This is a long message that takes 3 seconds to speak")
                            elapsed = time.time() - start_time
                            
                            # Should stop early (around 0.5-1s, not full 3s)
                            assert elapsed < 2.0, f"TTS should have been interrupted early, but took {elapsed}s"
                            interface.tts_engine.stop.assert_called()