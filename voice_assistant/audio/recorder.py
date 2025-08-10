"""Audio recording with VAD support."""

import collections
import json
import struct
import sys
import time
from pathlib import Path
from typing import Optional, List

import numpy as np
import pyaudio

try:
    import torch
    from silero_vad import load_silero_vad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False

from ..config import AudioConfig, VADConfig


class AudioRecorder:
    """Handles audio recording with optional VAD support."""
    
    def __init__(self, audio_config: AudioConfig, vad_config: VADConfig):
        self.audio_config = audio_config
        self.vad_config = vad_config
        self.audio = pyaudio.PyAudio()
        self.vad_model = None
        
        # Initialize VAD if available and enabled
        if VAD_AVAILABLE and vad_config.enabled:
            try:
                self.vad_model = load_silero_vad()
                print("✓ Silero VAD initialized")
            except Exception as e:
                print(f"Warning: Could not load VAD model: {e}")
                self.vad_model = None
        
        # Load or calibrate noise floor
        self._load_calibration()
    
    def _load_calibration(self):
        """Load saved noise floor calibration."""
        calibration_file = Path.home() / ".claude" / "noise_calibration.json"
        if calibration_file.exists():
            try:
                with open(calibration_file) as f:
                    data = json.load(f)
                    self.audio_config.noise_floor = data.get("noise_floor")
                    if self.audio_config.noise_floor:
                        adaptive_threshold = self.audio_config.noise_floor * 3
                        self.audio_config.silence_threshold = max(
                            adaptive_threshold, self.audio_config.silence_threshold
                        )
            except Exception:
                pass
    
    def _save_calibration(self):
        """Save noise floor calibration."""
        calibration_file = Path.home() / ".claude" / "noise_calibration.json"
        calibration_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(calibration_file, "w") as f:
            json.dump({"noise_floor": self.audio_config.noise_floor}, f)
    
    def calibrate_noise_floor(self):
        """Calibrate the noise floor for better silence detection."""
        print("🎤 Calibrating noise floor... Please remain quiet for 3 seconds.")
        
        stream = self.audio.open(
            format=getattr(pyaudio, f"pa{self.audio_config.format.title()}"),
            channels=self.audio_config.channels,
            rate=self.audio_config.sample_rate,
            input=True,
            frames_per_buffer=self.audio_config.chunk_size,
        )
        
        amplitudes = []
        for _ in range(self.audio_config.calibration_samples):
            data = stream.read(self.audio_config.chunk_size, exception_on_overflow=False)
            amplitude = self._get_audio_amplitude(data)
            amplitudes.append(amplitude)
        
        stream.stop_stream()
        stream.close()
        
        # Calculate noise floor as mean + 2 standard deviations
        self.audio_config.noise_floor = np.mean(amplitudes) + 2 * np.std(amplitudes)
        
        # Set silence threshold as 3x the noise floor
        adaptive_threshold = self.audio_config.noise_floor * 3
        self.audio_config.silence_threshold = max(adaptive_threshold, 1000)
        
        self._save_calibration()
        
        print(f"✓ Noise floor: {self.audio_config.noise_floor:.0f}")
        print(f"✓ Silence threshold: {self.audio_config.silence_threshold:.0f}")
    
    def _get_audio_amplitude(self, data: bytes) -> float:
        """Calculate amplitude of audio data."""
        count = len(data) / 2
        format_str = f"{int(count)}h"
        shorts = struct.unpack(format_str, data)
        return np.sqrt(np.mean(np.square(shorts)))
    
    def record_with_vad(self, timeout: Optional[float] = None, quiet: bool = False) -> Optional[List[bytes]]:
        """Record audio using Voice Activity Detection."""
        if not self.vad_model:
            return self.record_with_amplitude(timeout, quiet=quiet)
        
        stream = self.audio.open(
            format=getattr(pyaudio, f"pa{self.audio_config.format.title()}"),
            channels=self.audio_config.channels,
            rate=self.audio_config.sample_rate,
            input=True,
            frames_per_buffer=self.vad_config.chunk_size,
        )
        
        frames = []
        pre_buffer = collections.deque(maxlen=self.vad_config.pre_buffer_size)
        recording_started = False
        speech_detected = False
        consecutive_speech_count = 0
        silence_start_time = None
        start_time = time.time()
        last_activity_time = time.time()
        
        if not quiet:
            print("🎤 Listening... (speak now)")
        
        try:
            while True:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    if not recording_started:
                        break
                
                # Check inactivity timeout
                if (time.time() - last_activity_time) > self.vad_config.inactivity_timeout:
                    print("\n⏱️ Inactivity timeout - returning to wake mode")
                    break
                
                # Read audio chunk
                data = stream.read(self.vad_config.chunk_size, exception_on_overflow=False)
                
                # Convert to float32 for VAD
                audio_int16 = np.frombuffer(data, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                
                # Get speech probability from VAD
                speech_prob = self.vad_model(
                    torch.from_numpy(audio_float32), self.audio_config.sample_rate
                ).item()
                
                # Determine if this chunk contains speech
                if recording_started:
                    # Lower threshold to continue recording (avoid cutting off)
                    is_speech = speech_prob > self.vad_config.speech_continue_threshold
                else:
                    # Higher threshold to start recording (avoid false starts)
                    is_speech = speech_prob > self.vad_config.speech_start_threshold
                
                # Keep a rolling pre-buffer of chunks that might be speech
                if not recording_started and speech_prob > 0.6:
                    pre_buffer.append(data)
                    if not quiet and speech_prob > 0.7:
                        # Visual feedback: medium probability speech in pre-buffer
                        sys.stdout.write("▓")
                        sys.stdout.flush()
                
                if is_speech:
                    consecutive_speech_count += 1
                    last_activity_time = time.time()
                    
                    # Use consecutive_speech_needed for initial detection
                    required_chunks = (
                        self.vad_config.consecutive_speech_needed 
                        if not recording_started 
                        else self.vad_config.min_speech_chunks
                    )
                    
                    if not recording_started and consecutive_speech_count >= required_chunks:
                        if not quiet:
                            print(f"\n🗣️ Speech detected! (prob: {speech_prob:.2f})")
                        recording_started = True
                        speech_detected = True
                        # Add pre-buffer to capture speech onset
                        frames.extend(pre_buffer)
                        pre_buffer.clear()
                    
                    if recording_started:
                        frames.append(data)
                        silence_start_time = None
                        if not quiet:
                            # Visual feedback: high probability speech
                            sys.stdout.write("█")
                            sys.stdout.flush()
                else:
                    consecutive_speech_count = 0
                    
                    if recording_started:
                        frames.append(data)
                        if not quiet:
                            # Visual feedback: silence during recording
                            sys.stdout.write("░")
                            sys.stdout.flush()
                        
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif (time.time() - silence_start_time) > self.audio_config.silence_duration:
                            if not quiet:
                                print("\n✓ Recording complete")
                            break
        
        except KeyboardInterrupt:
            print("\n⚠️ Cancelled")
            return None
        finally:
            stream.stop_stream()
            stream.close()
        
        if not frames or not recording_started:
            return None
        
        # Smart trimming using VAD
        frames = self._trim_silence_with_vad(frames)
        
        return frames
    
    def _trim_silence_with_vad(self, frames: List[bytes]) -> List[bytes]:
        """Trim silence from the end using VAD."""
        if not self.vad_model or len(frames) < 20:
            return frames
        
        # Find last speech frame
        last_speech_index = len(frames) - 1
        for i in range(len(frames) - 1, -1, -1):
            audio_int16 = np.frombuffer(frames[i], dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            speech_prob = self.vad_model(
                torch.from_numpy(audio_float32), self.audio_config.sample_rate
            ).item()
            
            if speech_prob > 0.6:
                last_speech_index = i
                break
        
        # Keep a small amount of silence after speech (10 chunks ~= 320ms)
        trim_index = min(last_speech_index + 10, len(frames))
        return frames[:trim_index]
    
    def record_with_amplitude(self, timeout: Optional[float] = None, quiet: bool = False) -> Optional[List[bytes]]:
        """Record audio using amplitude-based detection (fallback)."""
        stream = self.audio.open(
            format=getattr(pyaudio, f"pa{self.audio_config.format.title()}"),
            channels=self.audio_config.channels,
            rate=self.audio_config.sample_rate,
            input=True,
            frames_per_buffer=self.audio_config.chunk_size,
        )
        
        frames = []
        silent_chunks = 0
        recording_started = False
        start_time = time.time()
        
        if not quiet:
            print("🎤 Listening... (amplitude-based)")
        
        try:
            while True:
                if timeout and (time.time() - start_time) > timeout:
                    if not recording_started:
                        break
                
                data = stream.read(self.audio_config.chunk_size, exception_on_overflow=False)
                amplitude = self._get_audio_amplitude(data)
                
                if amplitude > self.audio_config.silence_threshold:
                    if not recording_started:
                        if not quiet:
                            print("💬 Speech detected, recording...")
                        recording_started = True
                    frames.append(data)
                    silent_chunks = 0
                elif recording_started:
                    frames.append(data)
                    silent_chunks += 1
                    
                    silence_time = (
                        silent_chunks * self.audio_config.chunk_size / self.audio_config.sample_rate
                    )
                    if silence_time > self.audio_config.silence_duration:
                        if not quiet:
                            print("✓ Recording complete")
                        break
        
        except KeyboardInterrupt:
            print("\n⚠️ Cancelled")
            return None
        finally:
            stream.stop_stream()
            stream.close()
        
        if not frames:
            return None
        
        # Trim silence from the end
        if len(frames) > 20:
            frames = frames[:-10]
        
        return frames
    
    def cleanup(self):
        """Clean up audio resources."""
        self.audio.terminate()