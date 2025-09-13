"""Audio resampling utilities for optimal Whisper compatibility."""

import numpy as np
from scipy import signal
from typing import Optional


class AudioResampler:
    """Handles resampling audio to 16kHz for Whisper."""
    
    def __init__(self, source_rate: int, target_rate: int = 16000):
        """
        Initialize the resampler.
        
        Args:
            source_rate: The input sample rate in Hz
            target_rate: The target sample rate in Hz (default 16000 for Whisper)
        """
        self.source_rate = source_rate
        self.target_rate = target_rate
        self.needs_resampling = source_rate != target_rate
        
        if self.needs_resampling:
            # Calculate resampling ratio
            self.resample_ratio = self.target_rate / self.source_rate
            
            # For common rates, use optimized ratios
            if source_rate == 48000 and target_rate == 16000:
                self.up = 1
                self.down = 3
            elif source_rate == 44100 and target_rate == 16000:
                # 16000/44100 = 160/441
                self.up = 160
                self.down = 441
            elif source_rate == 32000 and target_rate == 16000:
                self.up = 1
                self.down = 2
            else:
                # General case - find a reasonable ratio
                from fractions import Fraction
                frac = Fraction(target_rate, source_rate).limit_denominator(1000)
                self.up = frac.numerator
                self.down = frac.denominator
    
    def resample(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Resample audio data to target rate.
        
        Args:
            audio_data: Input audio samples
            
        Returns:
            Resampled audio at target rate
        """
        if not self.needs_resampling:
            return audio_data
            
        # Use scipy's resample_poly for high quality resampling
        # This uses an anti-aliasing filter to prevent artifacts
        resampled = signal.resample_poly(audio_data, self.up, self.down)
        
        return resampled.astype(audio_data.dtype)
    
    def resample_chunk(self, chunk: bytes, format_bits: int = 16) -> bytes:
        """
        Resample a raw audio chunk.
        
        Args:
            chunk: Raw audio bytes
            format_bits: Bits per sample (16 or 32)
            
        Returns:
            Resampled audio bytes
        """
        if not self.needs_resampling:
            return chunk
            
        # Convert bytes to numpy array
        if format_bits == 16:
            audio_array = np.frombuffer(chunk, dtype=np.int16)
        elif format_bits == 32:
            audio_array = np.frombuffer(chunk, dtype=np.int32)
        else:
            raise ValueError(f"Unsupported format: {format_bits} bits")
            
        # Resample
        resampled_array = self.resample(audio_array)
        
        # Convert back to bytes
        return resampled_array.tobytes()
    
    def get_resampled_chunk_size(self, original_size: int) -> int:
        """
        Calculate the expected size of a resampled chunk.
        
        Args:
            original_size: Size of original chunk in samples
            
        Returns:
            Expected size after resampling
        """
        if not self.needs_resampling:
            return original_size
            
        return int(original_size * self.resample_ratio)
    
    @property
    def info(self) -> str:
        """Get information about the resampling configuration."""
        if not self.needs_resampling:
            return f"No resampling needed (already at {self.target_rate} Hz)"
        
        return (f"Resampling from {self.source_rate} Hz to {self.target_rate} Hz "
                f"(ratio: {self.up}/{self.down})")