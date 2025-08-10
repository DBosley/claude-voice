"""Tests for TTS modules."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from voice_assistant.tts import TTSEngine, PiperTTS, create_tts_engine
from voice_assistant.tts.base import TTSEngine as BaseTTS
from voice_assistant.config import TTSConfig


class TestBaseTTS:
    """Test base TTS functionality."""
    
    def test_preprocess_text(self):
        """Test text preprocessing."""
        # Create concrete implementation for testing
        class TestTTS(BaseTTS):
            @property
            def is_available(self):
                return True
            
            def speak(self, text, friendly=False):
                return True
            
            def stop(self):
                pass
        
        tts = TestTTS(voice="test", speech_rate=1.0)
        
        # Test whitespace normalization
        text = tts.preprocess_text("Hello   world")
        assert text == "Hello world"
        
        # Test ellipsis removal
        text = tts.preprocess_text("Hello... world")
        assert text == "Hello world"
        
        # Test dash replacement
        text = tts.preprocess_text("Hello--world")
        assert text == "Hello, world"


class TestPiperTTS:
    """Test Piper TTS functionality."""
    
    @pytest.fixture
    def piper_tts(self):
        """Create Piper TTS instance."""
        with patch.object(PiperTTS, '_check_installation'):
            return PiperTTS(voice="alan", speech_rate=1.0)
    
    def test_initialization(self, piper_tts):
        """Test Piper TTS initialization."""
        assert piper_tts.voice == "alan"
        assert piper_tts.speech_rate == 1.0
        assert piper_tts.is_speaking == False
    
    def test_voice_mapping(self):
        """Test voice file mapping."""
        assert PiperTTS.VOICE_FILES["alan"] == "en_GB-alan-medium.onnx"
        assert PiperTTS.VOICE_FILES["cori"] == "en_GB-cori-medium.onnx"
        assert PiperTTS.VOICE_FILES["british_male"] == "en_GB-alan-medium.onnx"
        assert PiperTTS.VOICE_FILES["british_female"] == "en_GB-cori-medium.onnx"
    
    @patch('voice_assistant.tts.piper.Path')
    def test_is_available(self, mock_path):
        """Test availability check."""
        with patch.object(PiperTTS, '_check_installation'):
            tts = PiperTTS()
        
        # Piper exists
        mock_path.home.return_value = MagicMock()
        tts.PIPER_PATH = MagicMock()
        tts.PIPER_PATH.exists.return_value = True
        assert tts.is_available == True
        
        # Piper doesn't exist
        tts.PIPER_PATH.exists.return_value = False
        assert tts.is_available == False
    
    def test_stop(self, piper_tts):
        """Test stop functionality."""
        piper_tts.stop()
        assert piper_tts.cancel_requested == True


class TestTTSFactory:
    """Test TTS factory functionality."""
    
    def test_create_auto_engine(self):
        """Test auto engine selection."""
        config = TTSConfig(engine="auto", voice="alan")
        
        with patch('voice_assistant.tts.factory.CoquiTTS') as mock_coqui:
            with patch('voice_assistant.tts.factory.PiperTTS') as mock_piper:
                # Coqui available
                mock_coqui.return_value.is_available = True
                engine = create_tts_engine(config)
                assert engine is not None
                mock_coqui.assert_called_once()
    
    def test_create_piper_engine(self):
        """Test Piper engine creation."""
        config = TTSConfig(engine="piper", voice="alan")
        
        with patch('voice_assistant.tts.factory.PiperTTS') as mock_piper:
            mock_piper.return_value.is_available = True
            engine = create_tts_engine(config)
            assert engine is not None
            mock_piper.assert_called_once()
    
    def test_no_engine_available(self):
        """Test when no engine is available."""
        config = TTSConfig(engine="auto")
        
        with patch('voice_assistant.tts.factory.CoquiTTS') as mock_coqui:
            with patch('voice_assistant.tts.factory.PiperTTS') as mock_piper:
                # No engines available
                mock_coqui.return_value.is_available = False
                mock_piper.return_value.is_available = False
                
                engine = create_tts_engine(config)
                assert engine is None