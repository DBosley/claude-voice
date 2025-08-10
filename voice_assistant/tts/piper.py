"""Piper TTS implementation."""

import random
import subprocess
import tempfile
from pathlib import Path

from .base import TTSEngine
from ..audio import AudioPlayer


class PiperTTS(TTSEngine):
    """Piper TTS engine for fast, lightweight speech synthesis."""
    
    PIPER_PATH = Path.home() / "scripts" / "piper"
    
    VOICE_FILES = {
        "alan": "en_GB-alan-medium.onnx",
        "cori": "en_GB-cori-medium.onnx",
        "british_male": "en_GB-alan-medium.onnx",
        "british_female": "en_GB-cori-medium.onnx",
    }
    
    FRIENDLY_PHRASES = [
        "Sure thing!",
        "Absolutely!",
        "You got it!",
        "Happy to help!",
        "Of course!",
        "Right away!",
        "My pleasure!",
        "Certainly!",
    ]
    
    def __init__(self, voice: str = "alan", speech_rate: float = 1.0):
        super().__init__(voice, speech_rate)
        self.audio_player = AudioPlayer(volume=0.5)
        self._check_installation()
    
    def _check_installation(self):
        """Check if Piper is installed."""
        if not self.PIPER_PATH.exists():
            print(f"Warning: Piper not found at {self.PIPER_PATH}")
            print("Install with: ~/scripts/install-piper-tts.sh")
    
    @property
    def is_available(self) -> bool:
        """Check if Piper TTS is available."""
        return self.PIPER_PATH.exists()
    
    def speak(self, text: str, friendly: bool = False) -> bool:
        """Speak text using Piper TTS."""
        if not self.is_available:
            return False
        
        text = self.preprocess_text(text)
        if not text:
            return True
        
        self.is_speaking = True
        self.cancel_requested = False
        
        try:
            # Add friendly prefix if requested
            if friendly:
                prefix = random.choice(self.FRIENDLY_PHRASES)
                text = f"{prefix} {text}"
            
            # Get voice file
            voice_file = self.VOICE_FILES.get(self.voice, "en_GB-alan-medium.onnx")
            voice_path = self.PIPER_PATH / voice_file
            
            if not voice_path.exists():
                print(f"Voice file not found: {voice_path}")
                return False
            
            # Generate audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                # Adjust speech rate (Piper uses length_scale, inverse of speed)
                length_scale = 1.0 / self.speech_rate
                
                cmd = [
                    str(self.PIPER_PATH / "piper"),
                    "--model", str(voice_path),
                    "--output_file", tmp_file.name,
                    "--length_scale", str(length_scale),
                ]
                
                # Run Piper
                result = subprocess.run(
                    cmd,
                    input=text.encode(),
                    capture_output=True,
                )
                
                if result.returncode != 0:
                    print(f"Piper error: {result.stderr.decode()}")
                    return False
                
                # Play the audio
                if not self.cancel_requested:
                    self.audio_player.play_file(Path(tmp_file.name), blocking=True)
                
                # Clean up
                Path(tmp_file.name).unlink(missing_ok=True)
                
                return not self.cancel_requested
                
        finally:
            self.is_speaking = False
    
    def stop(self):
        """Stop current speech."""
        self.cancel_requested = True
        self.audio_player.stop()