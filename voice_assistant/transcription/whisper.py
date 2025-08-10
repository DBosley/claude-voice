"""Whisper-based speech transcription."""

import tempfile
import wave
from typing import List, Optional

import numpy as np
import pyaudio

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    whisper = None

from ..config import TranscriptionConfig, AudioConfig


class WhisperTranscriber:
    """Handles speech-to-text using OpenAI Whisper."""
    
    def __init__(self, config: TranscriptionConfig, audio_config: AudioConfig):
        self.config = config
        self.audio_config = audio_config
        self.model = None
        
        if WHISPER_AVAILABLE:
            self._load_model()
        else:
            print("Warning: Whisper not installed. Install with: pip install openai-whisper")
    
    def _load_model(self):
        """Load the Whisper model."""
        if not WHISPER_AVAILABLE:
            return
        
        print(f"Loading Whisper model '{self.config.model_size}'...")
        try:
            self.model = whisper.load_model(self.config.model_size)
            print(f"✓ Whisper {self.config.model_size} model loaded")
        except Exception as e:
            print(f"Error loading Whisper model: {e}")
            self.model = None
    
    def transcribe(self, audio_frames: List[bytes]) -> Optional[str]:
        """Transcribe audio frames to text."""
        if not self.model or not audio_frames:
            return None
        
        # Save audio to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            with wave.open(tmp_file.name, "wb") as wf:
                wf.setnchannels(self.audio_config.channels)
                wf.setsampwidth(pyaudio.PyAudio().get_sample_size(
                    getattr(pyaudio, f"pa{self.audio_config.format.title()}")
                ))
                wf.setframerate(self.audio_config.sample_rate)
                wf.writeframes(b"".join(audio_frames))
            
            # Transcribe with Whisper
            print("🔄 Transcribing...")
            result = self.model.transcribe(
                tmp_file.name,
                language=self.config.language,
                task="transcribe",
                temperature=self.config.temperature,
                initial_prompt=self.config.initial_prompt,
            )
            
            text = result["text"].strip()
            
            # Handle minimum audio length
            audio_duration = len(audio_frames) * self.audio_config.chunk_size / self.audio_config.sample_rate
            if audio_duration < self.config.min_audio_length:
                return None
            
            # ASCII validation - filter non-ASCII characters
            try:
                text.encode('ascii')
            except UnicodeEncodeError:
                # Remove non-ASCII characters
                text = ''.join(char for char in text if ord(char) < 128)
            
            # Filter out noise (single characters, just punctuation, etc.)
            # But allow numbers and number sequences
            if len(text) <= 1 or text in [".", ",", "?", "!", "...", "---"]:
                return None
            
            return text
    
    def quick_transcribe(self, audio_frames: List[bytes]) -> Optional[str]:
        """Quick transcription for wake word detection (uses tiny model if available)."""
        if not WHISPER_AVAILABLE:
            return None
        
        # Use tiny model for speed
        if not hasattr(self, "_tiny_model"):
            try:
                self._tiny_model = whisper.load_model("tiny")
            except:
                self._tiny_model = self.model
        
        if not self._tiny_model:
            return None
        
        try:
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                with wave.open(tmp_file.name, "wb") as wf:
                    wf.setnchannels(self.audio_config.channels)
                    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(
                        getattr(pyaudio, f"pa{self.audio_config.format.title()}")
                    ))
                    wf.setframerate(self.audio_config.sample_rate)
                    wf.writeframes(b"".join(audio_frames))
                
                # Quick transcribe with tiny model
                result = self._tiny_model.transcribe(
                    tmp_file.name,
                    language="en",
                    task="transcribe",
                    temperature=0.0,
                )
                
                return result["text"].strip().lower()
        except:
            return None