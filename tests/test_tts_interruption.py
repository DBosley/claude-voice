"""Tests for TTS interruption functionality."""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import select

from voice_assistant.core.interface import VoiceInterface
from voice_assistant.config import Config


class TestTTSInterruption:
    """Test TTS interruption via ESC key and voice detection."""
    
    @pytest.fixture
    def interface(self):
        """Create a VoiceInterface instance for testing."""
        from voice_assistant.config import AudioConfig, VADConfig, TTSConfig, TranscriptionConfig, ProfileConfig
        
        config = Config(
            audio=AudioConfig(),
            vad=VADConfig(),
            tts=TTSConfig(engine="coqui"),
            transcription=TranscriptionConfig(),
            profiles=ProfileConfig()
        )
        interface = VoiceInterface(config)
        # Mock the TTS engine
        interface.tts_engine = Mock()
        interface.tts_engine.is_speaking = True
        interface.tts_engine.speak = Mock()
        interface.tts_engine.stop = Mock()
        return interface
    
    def test_esc_stops_tts_playback(self, interface):
        """Test that pressing ESC during TTS playback stops it immediately."""
        # Simulate TTS speaking
        interface.tts_engine.is_speaking = True
        
        # Mock stdin to simulate ESC key press
        with patch('sys.stdin') as mock_stdin:
            with patch('select.select') as mock_select:
                with patch('tty.setraw'):
                    with patch('termios.tcgetattr'):
                        with patch('termios.tcsetattr'):
                            # Simulate ESC key available and pressed
                            mock_select.return_value = ([mock_stdin], [], [])
                            mock_stdin.read.return_value = '\x1b'  # ESC key
                            
                            # Start TTS with some text
                            def simulate_speaking():
                                time.sleep(0.1)
                                interface.tts_engine.is_speaking = False
                            
                            speak_thread = threading.Thread(target=simulate_speaking)
                            speak_thread.start()
                            
                            # Call speak which should set up interrupt listener
                            interface.speak("This is a long text that should be interrupted")
                            
                            # Verify TTS was stopped
                            interface.tts_engine.stop.assert_called()
    
    def test_voice_interruption_after_1_second(self, interface):
        """Test that speaking for 1 second during TTS stops playback."""
        # Mock audio recorder to simulate voice detection
        interface.audio_recorder = Mock()
        interface.transcriber = Mock()
        
        # Simulate continuous speech for > 1 second
        speech_frames = [b'audio_data'] * 10
        interface.audio_recorder.record_with_amplitude = Mock(return_value=speech_frames)
        interface.audio_recorder.record_with_vad = Mock(return_value=speech_frames)
        interface.transcriber.transcribe = Mock(return_value="Stop talking please")
        
        # Simulate TTS speaking
        interface.tts_engine.is_speaking = True
        
        # Mock time to simulate 1 second passing
        with patch('time.time') as mock_time:
            # First call: speech starts
            # Second call: check if 1 second passed
            mock_time.side_effect = [0.0, 1.1, 1.2, 1.3]
            
            # Start speaking
            def simulate_tts():
                time.sleep(0.2)
                interface.tts_engine.is_speaking = False
            
            tts_thread = threading.Thread(target=simulate_tts)
            tts_thread.start()
            
            # Speak should detect interruption
            interface.speak("This text will be interrupted by voice")
            
            # Wait for threads to finish
            tts_thread.join(timeout=1)
            
            # Verify TTS was stopped
            interface.tts_engine.stop.assert_called()
            
            # Verify interrupted text was captured
            assert hasattr(interface, '_interrupted_text')
            assert interface._interrupted_text == "Stop talking please"