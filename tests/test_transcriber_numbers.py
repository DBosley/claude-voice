"""Test transcriber handling of number sequences."""

import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from voice_assistant.config import TranscriptionConfig, AudioConfig
from voice_assistant.transcription import WhisperTranscriber


def test_transcriber_allows_number_sequences():
    """Test that transcriber doesn't filter out sequences of numbers."""
    config = TranscriptionConfig()
    audio_config = AudioConfig()
    
    with patch('voice_assistant.transcription.whisper.WHISPER_AVAILABLE', True):
        with patch('voice_assistant.transcription.whisper.whisper') as mock_whisper:
            # Mock the model
            mock_model = Mock()
            mock_whisper.load_model.return_value = mock_model
            
            transcriber = WhisperTranscriber(config, audio_config)
            
            # Create fake audio frames
            audio_frames = [b'\x00' * 1024] * 100  # Enough for minimum duration
            
            # Test various number formats that should NOT be filtered
            test_cases = [
                "5 4 6 1 2",  # Numbers with spaces
                "12345",      # Pure digits (currently filtered - this will fail)
                "5, 4, 6, 1, 2",  # Numbers with commas
            ]
            
            for test_text in test_cases:
                mock_model.transcribe.return_value = {"text": test_text}
                result = transcriber.transcribe(audio_frames)
                assert result == test_text, f"Expected '{test_text}' but got {result}"