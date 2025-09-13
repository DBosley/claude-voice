"""Tests for audio modules."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from voice_assistant.audio import AudioRecorder, AudioPlayer
from voice_assistant.config import AudioConfig, VADConfig


class TestAudioRecorder:
    """Test audio recording functionality."""
    
    @pytest.fixture
    def audio_config(self):
        """Create test audio configuration."""
        return AudioConfig(
            chunk_size=1024,
            channels=1,
            sample_rate=16000,
            silence_threshold=1000,
            silence_duration=2.0
        )
    
    @pytest.fixture
    def vad_config(self):
        """Create test VAD configuration."""
        return VADConfig(
            enabled=False,  # Disable for testing
            speech_start_threshold=0.85,
            speech_continue_threshold=0.5
        )
    
    @pytest.fixture
    def recorder(self, audio_config, vad_config):
        """Create audio recorder."""
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            mock_audio = Mock()
            mock_audio.get_default_input_device_info.return_value = {
                'defaultSampleRate': 16000.0
            }
            mock_pyaudio.return_value = mock_audio
            return AudioRecorder(audio_config, vad_config)
    
    def test_recorder_initialization(self, recorder):
        """Test recorder initialization."""
        assert recorder.audio_config is not None
        assert recorder.vad_config is not None
        assert recorder.vad_model is None  # VAD disabled
    
    def test_get_audio_amplitude(self, recorder):
        """Test amplitude calculation."""
        # Create silent audio data
        silent_data = b'\x00' * 2048
        amplitude = recorder._get_audio_amplitude(silent_data)
        assert amplitude == 0.0
        
        # Create non-silent data
        noise_data = b'\x10\x00' * 1024
        amplitude = recorder._get_audio_amplitude(noise_data)
        assert amplitude > 0.0
    
    @patch('voice_assistant.audio.recorder.pyaudio.PyAudio')
    @patch('builtins.print')
    def test_record_with_amplitude_quiet_mode(self, mock_print, mock_pyaudio, audio_config, vad_config):
        """Test that quiet mode suppresses print statements in amplitude recording."""
        # Setup mock stream
        mock_stream = Mock()
        mock_stream.read.side_effect = [
            b'\x00' * 1024,  # Silent
            b'\x10' * 1024,  # Speech detected
            b'\x10' * 1024,  # More speech
            b'\x00' * 1024,  # Silent again (triggers completion after 2s)
        ] + [b'\x00' * 1024] * 100  # Lots of silence to trigger end
        mock_stream.close.return_value = None
        
        mock_audio = Mock()
        mock_audio.open.return_value = mock_stream
        mock_audio.get_default_input_device_info.return_value = {
            'defaultSampleRate': 16000.0
        }
        mock_pyaudio.return_value = mock_audio
        
        with patch('time.time') as mock_time:
            # Provide enough time values for the recording loop
            mock_time.side_effect = [0] + [i * 0.1 for i in range(100)]
            recorder = AudioRecorder(audio_config, vad_config)
            
            # Test with quiet=False (default)
            recorder.record_with_amplitude(timeout=3, quiet=False)
            
            # Should print listening message
            mock_print.assert_any_call("🎤 Listening... (amplitude-based)")
            mock_print.reset_mock()
            
            # Reset stream read side effects
            mock_stream.read.side_effect = [
                b'\x00' * 1024,  # Silent
                b'\x10' * 1024,  # Speech detected
                b'\x10' * 1024,  # More speech
                b'\x00' * 1024,  # Silent again
            ] + [b'\x00' * 1024] * 100
            
            # Test with quiet=True
            mock_time.side_effect = [0] + [i * 0.1 for i in range(100)]
            recorder.record_with_amplitude(timeout=3, quiet=True)
            
            # Should NOT print listening message when quiet
            assert not any("Listening... (amplitude-based)" in str(call) for call in mock_print.call_args_list)
    
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.exists')
    def test_load_calibration(self, mock_exists, mock_home, audio_config, vad_config):
        """Test loading calibration data."""
        # Mock calibration file existence
        mock_exists.return_value = True
        mock_home.return_value = Path("/tmp/test_home")
        
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = '{"noise_floor": 500.0}'
            
            with patch('json.load', return_value={"noise_floor": 500.0}):
                with patch('pyaudio.PyAudio'):
                    recorder = AudioRecorder(audio_config, vad_config)
                    
                    # Should load noise floor
                    assert recorder.audio_config.noise_floor == 500.0
                    # Should adjust threshold
                    assert recorder.audio_config.silence_threshold >= 1500.0
    
    @patch('pathlib.Path.home')
    def test_save_calibration(self, mock_home, recorder):
        """Test saving calibration data."""
        recorder.audio_config.noise_floor = 750.0
        
        # Use a temp directory that actually exists
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_home.return_value = Path(tmpdir)
            
            with patch('json.dump') as mock_dump:
                recorder._save_calibration()
                
                # Should save noise floor
                mock_dump.assert_called_once()
                saved_data = mock_dump.call_args[0][0]
                assert saved_data["noise_floor"] == 750.0


class TestAudioPlayer:
    """Test audio playback functionality."""
    
    @pytest.fixture
    def player(self):
        """Create audio player."""
        return AudioPlayer(volume=0.5)
    
    def test_player_initialization(self, player):
        """Test player initialization."""
        assert player.volume == 0.5
        assert player.is_playing == False
        assert player.cancel_requested == False
    
    def test_is_busy_property(self, player):
        """Test is_busy property."""
        assert player.is_busy == False
        
        player.is_playing = True
        assert player.is_busy == True
    
    def test_stop_request(self, player):
        """Test stop request."""
        player.stop()
        assert player.cancel_requested == True
    
    @patch('subprocess.run')
    def test_play_with_paplay(self, mock_run, player):
        """Test playing audio with paplay."""
        # Create temp audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            audio_file = Path(tmp.name)
            tmp.write(b"fake audio data")
        
        try:
            # Mock successful playback
            mock_run.return_value.returncode = 0
            
            result = player._play_with_paplay(audio_file, blocking=True)
            assert result == True
            
            # Check command
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "paplay" in cmd
            assert str(audio_file) in cmd
            
        finally:
            audio_file.unlink()