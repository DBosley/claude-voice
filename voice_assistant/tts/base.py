"""Base class for TTS engines."""

from abc import ABC, abstractmethod
from typing import Optional


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""
    
    def __init__(self, voice: str, speech_rate: float = 1.0):
        self.voice = voice
        self.speech_rate = speech_rate
        self.is_speaking = False
        self.cancel_requested = False
    
    @abstractmethod
    def speak(self, text: str, friendly: bool = False) -> bool:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to speak
            friendly: Whether to use a friendlier tone
            
        Returns:
            True if speech completed successfully
        """
        pass
    
    @abstractmethod
    def stop(self):
        """Stop current speech."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this TTS engine is available."""
        pass
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text before TTS."""
        # Handle common replacements first
        replacements = {
            "...": " ",
            "..": " ",
            "--": ", ",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove excessive whitespace after replacements
        text = " ".join(text.split())
        
        return text.strip()