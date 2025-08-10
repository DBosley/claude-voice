"""Tests for configuration module."""

import pytest
from pathlib import Path

from voice_assistant.config import Config, AudioConfig, TTSConfig, VADConfig, TranscriptionConfig, ProfileConfig


class TestConfig:
    """Test configuration management."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = Config.default()
        
        assert isinstance(config.audio, AudioConfig)
        assert isinstance(config.tts, TTSConfig)
        assert isinstance(config.vad, VADConfig)
        assert config.wake_word == "hey claude"
        assert config.audio.sample_rate == 16000
        assert config.tts.engine == "auto"
    
    def test_config_from_args(self):
        """Test configuration from arguments."""
        config = Config.from_args(
            model_size="small",
            wake_word="hello assistant",
            voice="alan",
            speech_rate=1.5,
            tts_engine="piper",
            silence_threshold=2000
        )
        
        assert config.transcription.model_size == "small"
        assert config.wake_word == "hello assistant"
        assert config.tts.voice == "alan"
        assert config.tts.speech_rate == 1.5
        assert config.tts.engine == "piper"
        assert config.audio.silence_threshold == 2000
    
    def test_audio_config_defaults(self):
        """Test audio configuration defaults."""
        audio = AudioConfig()
        
        assert audio.chunk_size == 1024
        assert audio.channels == 1
        assert audio.sample_rate == 16000
        assert audio.format == "int16"
        assert audio.silence_duration == 2.0
    
    def test_vad_config_defaults(self):
        """Test VAD configuration defaults."""
        vad = VADConfig()
        
        assert vad.enabled == True
        assert vad.speech_start_threshold == 0.85
        assert vad.speech_continue_threshold == 0.5
        assert vad.pre_buffer_size == 10
        assert vad.inactivity_timeout == 120.0
    
    def test_tts_config_defaults(self):
        """Test TTS configuration defaults."""
        tts = TTSConfig()
        
        assert tts.engine == "auto"
        assert tts.voice == "british_male"
        assert tts.speech_rate == 1.1
        assert tts.natural_speech == True
        assert tts.volume == 0.5
    
    def test_profile_config_defaults(self):
        """Test profile configuration defaults."""
        profile = ProfileConfig()
        
        assert profile.context_dir == Path(".context")
        assert profile.current_profile is None
        assert profile.profile_state_file == Path.home() / ".claude" / "voice_profile_state.json"