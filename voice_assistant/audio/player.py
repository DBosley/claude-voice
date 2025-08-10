"""Audio playback functionality."""

import subprocess
import threading
from pathlib import Path
from typing import Optional

try:
    import sounddevice as sd
    import soundfile as sf
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AudioPlayer:
    """Handles audio playback."""
    
    def __init__(self, volume: float = 0.5):
        self.volume = volume
        self.is_playing = False
        self.cancel_requested = False
        self._lock = threading.Lock()
    
    def play_file(self, audio_file: Path, blocking: bool = True) -> bool:
        """Play an audio file."""
        if not audio_file.exists():
            return False
        
        with self._lock:
            if self.is_playing:
                return False
            self.is_playing = True
            self.cancel_requested = False
        
        try:
            if SOUNDDEVICE_AVAILABLE:
                return self._play_with_sounddevice(audio_file, blocking)
            else:
                return self._play_with_paplay(audio_file, blocking)
        finally:
            with self._lock:
                self.is_playing = False
    
    def _play_with_sounddevice(self, audio_file: Path, blocking: bool) -> bool:
        """Play audio using sounddevice."""
        try:
            data, samplerate = sf.read(str(audio_file))
            
            # Apply volume
            data = data * self.volume
            
            if blocking:
                sd.play(data, samplerate)
                sd.wait()
            else:
                sd.play(data, samplerate)
            
            return True
        except Exception as e:
            print(f"Error playing audio with sounddevice: {e}")
            return False
    
    def _play_with_paplay(self, audio_file: Path, blocking: bool) -> bool:
        """Play audio using paplay (PulseAudio)."""
        try:
            volume_percent = int(self.volume * 100)
            cmd = ["paplay", "--volume", str(volume_percent * 655), str(audio_file)]
            
            if blocking:
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            else:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
        except Exception as e:
            print(f"Error playing audio with paplay: {e}")
            return False
    
    def stop(self):
        """Request stop of current playback."""
        with self._lock:
            self.cancel_requested = True
            if SOUNDDEVICE_AVAILABLE:
                try:
                    sd.stop()
                except:
                    pass
    
    @property
    def is_busy(self) -> bool:
        """Check if currently playing audio."""
        with self._lock:
            return self.is_playing