"""Tests for automatic audio resampling."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_assistant.config import AudioConfig, VADConfig


class TestAudioResampling:
    """Test automatic sample rate detection and resampling."""

    def test_recorder_detects_device_sample_rate(self):
        """Test that AudioRecorder detects the actual device sample rate."""
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock device that only supports 48000 Hz
            mock_audio = Mock()
            mock_device_info = {
                'name': 'Test Device',
                'defaultSampleRate': 48000.0,
                'maxInputChannels': 2
            }
            mock_audio.get_default_input_device_info.return_value = mock_device_info
            mock_pyaudio.return_value = mock_audio
            
            # Create recorder with 16000 Hz config
            audio_config = AudioConfig(sample_rate=16000)
            vad_config = VADConfig()
            
            from voice_assistant.audio.recorder import AudioRecorder
            recorder = AudioRecorder(audio_config, vad_config)
            
            # Recorder should detect the device uses 48000 Hz
            assert hasattr(recorder, 'device_sample_rate')
            assert recorder.device_sample_rate == 48000
    
    def test_recorder_creates_resampler_when_rates_differ(self):
        """Test that AudioRecorder creates a resampler when sample rates differ."""
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock device that uses 48000 Hz
            mock_audio = Mock()
            mock_device_info = {
                'name': 'Test Device',
                'defaultSampleRate': 48000.0,
                'maxInputChannels': 2
            }
            mock_audio.get_default_input_device_info.return_value = mock_device_info
            mock_pyaudio.return_value = mock_audio
            
            # Create recorder with 16000 Hz config (for Whisper)
            audio_config = AudioConfig(sample_rate=16000)
            vad_config = VADConfig()
            
            from voice_assistant.audio.recorder import AudioRecorder
            recorder = AudioRecorder(audio_config, vad_config)
            
            # Recorder should create a resampler
            assert hasattr(recorder, 'resampler')
            assert recorder.resampler is not None
            assert recorder.resampler.source_rate == 48000
            assert recorder.resampler.target_rate == 16000
    
    def test_recorder_logs_sample_rate_info_in_verbose_mode(self):
        """Test that AudioRecorder logs sample rate info when verbose is enabled."""
        with patch('pyaudio.PyAudio') as mock_pyaudio:
            # Mock device that uses 48000 Hz
            mock_audio = Mock()
            mock_device_info = {
                'name': 'Test Device',
                'defaultSampleRate': 48000.0,
                'maxInputChannels': 2
            }
            mock_audio.get_default_input_device_info.return_value = mock_device_info
            mock_pyaudio.return_value = mock_audio
            
            # Create recorder with verbose config
            audio_config = AudioConfig(sample_rate=16000)
            vad_config = VADConfig()
            
            with patch('builtins.print') as mock_print:
                from voice_assistant.audio.recorder import AudioRecorder
                recorder = AudioRecorder(audio_config, vad_config, verbose=True)
                
                # Should log device sample rate detection
                mock_print.assert_any_call("🎤 Detected device sample rate: 48000 Hz")
                # Should log resampler creation
                mock_print.assert_any_call("🔄 Creating resampler: 48000 Hz → 16000 Hz for optimal Whisper performance")