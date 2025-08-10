"""Configuration settings for Voice Assistant."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AudioConfig:
    """Audio recording and playback configuration."""

    chunk_size: int = 1024
    channels: int = 1
    sample_rate: int = 16000  # Can be overridden (e.g., 48000 for some headsets)
    format: str = "int16"
    silence_threshold: int = 1000
    silence_duration: float = 2.0
    noise_floor: Optional[float] = None
    calibration_samples: int = 50
    


@dataclass
class VADConfig:
    """Voice Activity Detection configuration."""

    enabled: bool = True
    speech_start_threshold: float = 0.85
    speech_continue_threshold: float = 0.5
    pre_buffer_size: int = 10
    chunk_size: int = 512
    min_speech_chunks: int = 3  # Minimum consecutive chunks to start recording
    consecutive_speech_needed: int = 2  # For initial detection
    inactivity_timeout: float = 120.0  # 2 minutes


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""

    engine: str = "auto"  # auto, coqui, piper
    voice: str = "british_male"  # british_male, british_female, alan, cori
    speech_rate: float = 1.1
    natural_speech: bool = True
    volume: float = 0.5
    sentence_delay: float = 0.5


@dataclass
class TranscriptionConfig:
    """Whisper transcription configuration."""

    model_size: str = "base"
    language: str = "en"
    temperature: float = 0.0
    initial_prompt: Optional[str] = None
    min_audio_length: float = 0.5


@dataclass
class ProfileConfig:
    """Profile management configuration."""

    context_dir: Path = Path(".context")
    current_profile: Optional[str] = None
    profile_state_file: Path = Path.home() / ".claude" / "voice_profile_state.json"


@dataclass
class Config:
    """Main configuration container."""

    audio: AudioConfig
    vad: VADConfig
    tts: TTSConfig
    transcription: TranscriptionConfig
    profiles: ProfileConfig
    wake_word: str = "hey claude"
    verbose: bool = False
    
    @classmethod
    def default(cls) -> "Config":
        """Create default configuration."""
        return cls(
            audio=AudioConfig(),
            vad=VADConfig(),
            tts=TTSConfig(),
            transcription=TranscriptionConfig(),
            profiles=ProfileConfig(),
        )
    
    @classmethod
    def from_args(cls, **kwargs) -> "Config":
        """Create configuration from command-line arguments."""
        config = cls.default()
        
        # Update relevant fields from kwargs
        if "model_size" in kwargs:
            config.transcription.model_size = kwargs["model_size"]
        if "wake_word" in kwargs:
            config.wake_word = kwargs["wake_word"].lower()
        if "voice" in kwargs:
            config.tts.voice = kwargs["voice"]
        if "speech_rate" in kwargs:
            config.tts.speech_rate = kwargs["speech_rate"]
        if "tts_engine" in kwargs:
            config.tts.engine = kwargs["tts_engine"]
        if "silence_threshold" in kwargs:
            config.audio.silence_threshold = kwargs["silence_threshold"]
        if "sample_rate" in kwargs:
            config.audio.sample_rate = kwargs["sample_rate"]
        if "verbose" in kwargs:
            config.verbose = kwargs["verbose"]
            
        return config