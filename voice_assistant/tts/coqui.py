"""Coqui TTS implementation."""

import queue
import re
import tempfile
import threading
from pathlib import Path
from typing import List, Optional

from .base import TTSEngine
from ..audio import AudioPlayer

try:
    # Workaround for PyTorch 2.6+ weights_only issue
    import torch
    original_load = torch.load
    torch.load = lambda *args, **kwargs: original_load(
        *args, **{k: v for k, v in kwargs.items() if k != "weights_only"}, weights_only=False
    )
    
    from TTS.api import TTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    TTS = None


class CoquiTTS(TTSEngine):
    """Coqui TTS engine with natural-sounding voices."""
    
    VOICE_MAPPING = {
        "british_male": "p258",
        "british_female": "p287",
        "p258": "p258",  # Male
        "p287": "p287",  # Female
    }
    
    def __init__(self, voice: str = "british_male", speech_rate: float = 1.1):
        super().__init__(voice, speech_rate)
        self.model = None
        self.audio_player = AudioPlayer(volume=0.5)
        self._audio_queue = queue.Queue()
        self._playback_thread = None
        
        if COQUI_AVAILABLE:
            self._init_model()
    
    def _init_model(self):
        """Initialize Coqui TTS model."""
        try:
            print("Loading Coqui TTS model (this may take a moment)...")
            self.model = TTS("tts_models/en/vctk/vits")
            print("✓ Coqui TTS model loaded")
        except Exception as e:
            print(f"Error loading Coqui TTS: {e}")
            self.model = None
    
    @property
    def is_available(self) -> bool:
        """Check if Coqui TTS is available."""
        return COQUI_AVAILABLE and self.model is not None
    
    def speak(self, text: str, friendly: bool = False) -> bool:
        """Speak text using Coqui TTS with sentence streaming."""
        if not self.is_available:
            return False
        
        text = self.preprocess_text(text)
        if not text:
            return True
        
        self.is_speaking = True
        self.cancel_requested = False
        
        try:
            # Split into sentences for streaming
            sentences = self._split_sentences(text)
            
            # Clear the queue
            while not self._audio_queue.empty():
                self._audio_queue.get()
            
            # Start playback thread if not running
            if self._playback_thread is None or not self._playback_thread.is_alive():
                self._playback_thread = threading.Thread(target=self._playback_worker)
                self._playback_thread.daemon = True
                self._playback_thread.start()
            
            # Generate audio for each sentence
            for sentence in sentences:
                if self.cancel_requested or not sentence:
                    break
                
                audio_file = self._generate_audio(sentence, friendly)
                if audio_file:
                    self._audio_queue.put(audio_file)
            
            # Wait for playback to complete
            self._audio_queue.put(None)  # Signal end
            if self._playback_thread:
                self._playback_thread.join(timeout=30)
            
            return not self.cancel_requested
            
        finally:
            self.is_speaking = False
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences for streaming with smart splitting."""
        # First split on sentence endings AND dashes
        sentences = re.split(r'(?<=[.!?])\s+|\s+-\s+', text)
        
        final_sentences = []
        for sentence in sentences:
            # Further split long sentences on commas if needed
            if len(sentence) > 150:  # Original threshold was 150
                # Split on commas but protect numbers like "1,000"
                parts = re.split(r',\s+(?![0-9])', sentence)
                if len(parts) > 1:
                    for part in parts[:-1]:
                        final_sentences.append(part + ",")
                    final_sentences.append(parts[-1])
                else:
                    final_sentences.append(sentence)
            else:
                # Don't split short sentences on commas unless very long
                if len(sentence) > 100:
                    # Only split if there are multiple commas
                    comma_count = sentence.count(',')
                    if comma_count > 2:
                        parts = re.split(r',\s+(?![0-9])', sentence)
                        if len(parts) > 1:
                            for part in parts[:-1]:
                                final_sentences.append(part + ",")
                            final_sentences.append(parts[-1])
                        else:
                            final_sentences.append(sentence)
                    else:
                        final_sentences.append(sentence)
                else:
                    final_sentences.append(sentence)
        
        return [s.strip() for s in final_sentences if s.strip()]
    
    def _generate_audio(self, text: str, friendly: bool) -> Optional[Path]:
        """Generate audio file for text."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                speaker = self.VOICE_MAPPING.get(self.voice, "p258")
                
                # Friendly parameter no longer modifies text
                # Coqui handles prosody well with proper punctuation
                
                # Suppress Coqui's verbose output
                import sys
                import io
                old_stdout = sys.stdout
                old_stderr = sys.stderr
                sys.stdout = io.StringIO()
                sys.stderr = io.StringIO()
                
                try:
                    # Generate audio
                    self.model.tts_to_file(
                        text=text,
                        speaker=speaker,
                        file_path=tmp_file.name,
                        speed=self.speech_rate,
                    )
                finally:
                    # Restore output streams
                    sys.stdout = old_stdout
                    sys.stderr = old_stderr
                
                return Path(tmp_file.name)
        except Exception as e:
            print(f"Error generating audio: {e}")
            return None
    
    
    def _playback_worker(self):
        """Worker thread for audio playback."""
        while True:
            try:
                audio_file = self._audio_queue.get(timeout=1)
                
                if audio_file is None:  # End signal
                    break
                
                if self.cancel_requested:
                    # Clean up remaining files
                    while not self._audio_queue.empty():
                        f = self._audio_queue.get()
                        if f and f.exists():
                            f.unlink()
                    break
                
                # Play the audio
                self.audio_player.play_file(audio_file, blocking=True)
                
                # Clean up temp file
                if audio_file.exists():
                    audio_file.unlink()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Playback error: {e}")
    
    def stop(self):
        """Stop current speech."""
        self.cancel_requested = True
        self.audio_player.stop()
        
        # Clear the queue
        while not self._audio_queue.empty():
            try:
                f = self._audio_queue.get_nowait()
                if f and f.exists():
                    f.unlink()
            except:
                pass