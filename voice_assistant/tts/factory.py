"""Factory for creating TTS engines."""

from typing import Optional

from .base import TTSEngine
from .coqui import CoquiTTS
from .piper import PiperTTS
from ..config import TTSConfig


def create_tts_engine(config: TTSConfig) -> Optional[TTSEngine]:
    """
    Create a TTS engine based on configuration.
    
    Args:
        config: TTS configuration
        
    Returns:
        TTS engine instance or None if no engine available
    """
    engine_type = config.engine
    
    if engine_type == "coqui":
        engine = CoquiTTS(voice=config.voice, speech_rate=config.speech_rate)
        if engine.is_available:
            return engine
            
    elif engine_type == "piper":
        engine = PiperTTS(voice=config.voice, speech_rate=config.speech_rate)
        if engine.is_available:
            return engine
            
    elif engine_type == "auto":
        # Try Coqui first for better quality
        if config.natural_speech:
            engine = CoquiTTS(voice=config.voice, speech_rate=config.speech_rate)
            if engine.is_available:
                print("Using Coqui TTS for natural speech")
                return engine
        
        # Fall back to Piper
        engine = PiperTTS(voice=config.voice, speech_rate=config.speech_rate)
        if engine.is_available:
            print("Using Piper TTS")
            return engine
    
    print("Warning: No TTS engine available")
    return None