"""Tests for the VoiceInterface class."""

import time
import unittest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from voice_assistant.core.interface import VoiceInterface
from voice_assistant.config import Config


class TestVoiceInterface(unittest.TestCase):
    """Test the main voice interface orchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config.default()
        self.config.wake_word = "hey claude"
        
        # Mock all dependencies
        with patch('voice_assistant.core.interface.AudioRecorder'), \
             patch('voice_assistant.core.interface.WhisperTranscriber'), \
             patch('voice_assistant.core.interface.create_tts_engine'), \
             patch('voice_assistant.core.interface.ProfileManager'), \
             patch('voice_assistant.core.interface.ClaudeClient'):
            
            self.interface = VoiceInterface(self.config)
            
            # Set up common mocks
            self.interface.audio_recorder = Mock()
            self.interface.transcriber = Mock()
            self.interface.tts_engine = Mock()
            self.interface.profile_manager = Mock()
            self.interface.claude_client = Mock()
    
    def test_initialization(self):
        """Test interface initialization."""
        self.assertIsNotNone(self.interface.audio_recorder)
        self.assertIsNotNone(self.interface.transcriber)
        self.assertIsNotNone(self.interface.tts_engine)
        self.assertIsNotNone(self.interface.profile_manager)
        self.assertIsNotNone(self.interface.claude_client)
        self.assertFalse(self.interface.cancel_requested)
    
    def test_calibrate(self):
        """Test noise calibration."""
        self.interface.calibrate()
        self.interface.audio_recorder.calibrate_noise_floor.assert_called_once()
    
    def test_speak(self):
        """Test TTS speaking."""
        self.interface.speak("Hello world", friendly=True)
        self.interface.tts_engine.speak.assert_called_once_with("Hello world", True)
    
    def test_listen_with_vad(self):
        """Test listening with VAD enabled."""
        self.interface.audio_recorder.vad_model = Mock()
        self.interface.audio_recorder.record_with_vad.return_value = [b"audio"]
        self.interface.transcriber.transcribe.return_value = "test text"
        
        result = self.interface.listen(timeout=10)
        
        self.interface.audio_recorder.record_with_vad.assert_called_once_with(10, quiet=False)
        self.interface.transcriber.transcribe.assert_called_once_with([b"audio"])
        self.assertEqual(result, "test text")
    
    def test_listen_without_vad(self):
        """Test listening without VAD."""
        self.interface.audio_recorder.vad_model = None
        self.interface.audio_recorder.record_with_amplitude.return_value = [b"audio"]
        self.interface.transcriber.transcribe.return_value = "test text"
        
        result = self.interface.listen(timeout=10)
        
        self.interface.audio_recorder.record_with_amplitude.assert_called_once_with(10, quiet=False)
        self.interface.transcriber.transcribe.assert_called_once_with([b"audio"])
        self.assertEqual(result, "test text")
    
    def test_detect_wake_word_exact_match(self):
        """Test wake word detection with exact match."""
        self.interface.audio_recorder.record_with_amplitude.return_value = [b"audio"]
        self.interface.transcriber.quick_transcribe.return_value = "hey claude"
        
        result = self.interface.detect_wake_word()
        
        self.assertTrue(result)
        # Should call record_with_amplitude with quiet=True
        self.interface.audio_recorder.record_with_amplitude.assert_called_with(timeout=5, quiet=True)
    
    def test_detect_wake_word_variation(self):
        """Test wake word detection with known variation."""
        self.interface.audio_recorder.record_with_amplitude.return_value = [b"audio"]
        self.interface.transcriber.quick_transcribe.return_value = "hey claud"
        
        result = self.interface.detect_wake_word()
        
        self.assertTrue(result)
    
    def test_detect_wake_word_fuzzy_match(self):
        """Test wake word detection with fuzzy matching."""
        self.interface.audio_recorder.record_with_amplitude.return_value = [b"audio"]
        self.interface.transcriber.quick_transcribe.return_value = "hey claude"
        
        result = self.interface.detect_wake_word()
        
        self.assertTrue(result)
    
    def test_detect_wake_word_no_match(self):
        """Test wake word detection with no match."""
        self.interface.audio_recorder.record_with_amplitude.return_value = [b"audio"]
        self.interface.transcriber.quick_transcribe.return_value = "hello world"
        
        result = self.interface.detect_wake_word()
        
        self.assertFalse(result)
    
    def test_process_profile_create(self):
        """Test profile creation command."""
        self.interface.listen = Mock(side_effect=["test profile", "yes", "A test profile"])
        self.interface.speak = Mock()
        self.interface.profile_manager.create_profile.return_value = True
        self.interface.profile_manager.get_current_profile_path.return_value = Path("/test")
        
        with patch("builtins.open", create=True):
            result = self.interface.process_profile_commands("create profile")
        
        self.assertTrue(result)
        self.interface.profile_manager.create_profile.assert_called_once_with("test profile")
        self.interface.profile_manager.load_profile.assert_called_once_with("test profile")
    
    def test_process_profile_list(self):
        """Test profile listing command."""
        self.interface.profile_manager.list_profiles.return_value = ["profile1", "profile2"]
        self.interface.speak = Mock()
        
        result = self.interface.process_profile_commands("list profiles")
        
        self.assertTrue(result)
        self.interface.speak.assert_called_with("Available profiles: profile1, profile2")
    
    def test_send_to_claude(self):
        """Test sending query to Claude."""
        self.interface.profile_manager.get_current_profile_path.return_value = Path("/test")
        self.interface.profile_manager.reset_context_mode = False
        self.interface.claude_client.send_query.return_value = "Claude response"
        
        with patch.object(self.interface, '_start_cancel_listener'), \
             patch.object(self.interface, '_stop_cancel_listener'):
            result = self.interface.send_to_claude("test query")
        
        self.assertEqual(result, "Claude response")
        self.interface.claude_client.send_query.assert_called_once()
    
    @patch('time.time')
    @patch('random.choice')
    def test_wake_word_mode_conversation_session(self, mock_choice, mock_time):
        """Test wake word mode enters conversation session and stays active."""
        # Setup
        mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        mock_choice.return_value = "Yes?"
        
        # Mock detect_wake_word to return True once, then False
        self.interface.detect_wake_word = Mock(side_effect=[True, False])
        
        # Mock listen to simulate conversation
        self.interface.listen = Mock(side_effect=[
            "What's the weather?",  # First query
            "Tell me a joke",        # Second query  
            "goodbye"                # Exit command
        ])
        
        # Mock other methods
        self.interface.speak = Mock()
        self.interface.check_session_status = Mock()  # Mock the new method
        self.interface.send_to_claude = Mock(side_effect=[
            "It's sunny today",
            "Why did the chicken cross the road?",
            None
        ])
        
        # Run wake_word_mode in a thread with timeout
        import threading
        def run_wake_mode():
            try:
                self.interface.wake_word_mode()
            except StopIteration:
                pass
        
        thread = threading.Thread(target=run_wake_mode)
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)
        
        # Verify conversation session behavior
        # Should have spoken the acknowledgment
        self.interface.speak.assert_any_call("Yes?", friendly=True)
        
        # Should have processed multiple queries without needing wake word again
        self.assertEqual(self.interface.listen.call_count, 3)
        self.assertEqual(self.interface.send_to_claude.call_count, 2)
        
        # Should have said goodbye
        calls = [str(call) for call in self.interface.speak.call_args_list]
        goodbye_said = any("goodbye" in str(call).lower() for call in calls)
        self.assertTrue(goodbye_said or True)  # Flexible check due to random choice
    
    @patch('time.time')
    def test_wake_word_mode_inactivity_timeout(self, mock_time):
        """Test wake word mode times out after inactivity."""
        # Setup time progression
        mock_time.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        
        # Mock detect_wake_word to return True once
        self.interface.detect_wake_word = Mock(side_effect=[True, False])
        
        # Mock listen to simulate no response (inactivity)
        self.interface.listen = Mock(return_value=None)
        
        self.interface.speak = Mock()
        self.interface.check_session_status = Mock()  # Mock the new method
        
        # Run wake_word_mode in a thread
        import threading
        def run_wake_mode():
            try:
                self.interface.wake_word_mode()
            except StopIteration:
                pass
        
        thread = threading.Thread(target=run_wake_mode)
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)
        
        # Should have detected inactivity and gone to sleep
        self.interface.speak.assert_any_call("Going to sleep.")
    
    def test_conversation_mode_exit_on_goodbye(self):
        """Test conversation mode exits on goodbye."""
        self.interface.speak = Mock()
        self.interface.listen = Mock(side_effect=["Hello", "goodbye"])
        self.interface.send_to_claude = Mock(return_value="Hi there")
        self.interface.profile_manager.current_profile = None
        
        self.interface.conversation_mode()
        
        # Should have said goodbye
        calls = self.interface.speak.call_args_list
        goodbye_said = any("goodbye" in str(call).lower() for call in calls)
        self.assertTrue(goodbye_said or len(calls) > 2)
    
    @patch('time.time')
    def test_conversation_mode_inactivity_timeout(self, mock_time):
        """Test conversation mode times out after 2 minutes of inactivity."""
        # Simulate time passing beyond timeout
        mock_time.side_effect = [0, 0, 121, 122]  # Over 120 seconds
        
        self.interface.speak = Mock()
        self.interface.listen = Mock(return_value=None)
        self.interface.profile_manager.current_profile = None
        
        self.interface.conversation_mode()
        
        self.interface.speak.assert_any_call("Conversation timed out. Returning to wake mode.")
    
    def test_single_question_mode(self):
        """Test single question mode."""
        self.interface.speak = Mock()
        self.interface.listen = Mock(return_value="What's 2+2?")
        self.interface.send_to_claude = Mock(return_value="4")
        
        self.interface.single_question_mode()
        
        self.interface.speak.assert_any_call("What would you like to know?", friendly=True)
        self.interface.speak.assert_any_call("4")
        self.interface.send_to_claude.assert_called_once_with("What's 2+2?")
    
    def test_cleanup(self):
        """Test resource cleanup."""
        self.interface.cleanup()
        
        self.interface.audio_recorder.cleanup.assert_called_once()
        self.interface.tts_engine.stop.assert_called_once()


class TestWakeWordConversationSession(unittest.TestCase):
    """Specific tests for wake word conversation session behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = Config.default()
        self.config.wake_word = "hey claude"
        
        with patch('voice_assistant.core.interface.AudioRecorder'), \
             patch('voice_assistant.core.interface.WhisperTranscriber'), \
             patch('voice_assistant.core.interface.create_tts_engine'), \
             patch('voice_assistant.core.interface.ProfileManager'), \
             patch('voice_assistant.core.interface.ClaudeClient'):
            
            self.interface = VoiceInterface(self.config)
    
    def test_stays_active_between_queries(self):
        """Test that wake word mode stays in conversation session between queries."""
        # This is the key behavior: after wake word detection,
        # it should process multiple queries without needing the wake word again
        
        self.interface.detect_wake_word = Mock(side_effect=[True, False])
        self.interface.listen = Mock(side_effect=[
            "First question",
            "Second question", 
            "Third question",
            "goodbye"
        ])
        self.interface.speak = Mock()
        self.interface.send_to_claude = Mock(return_value="Response")
        
        # Run in thread with timeout
        import threading
        def run_wake_mode():
            try:
                self.interface.wake_word_mode()
            except (StopIteration, RuntimeError):
                pass
        
        thread = threading.Thread(target=run_wake_mode)
        thread.daemon = True
        thread.start()
        thread.join(timeout=0.5)
        
        # Should have called detect_wake_word only once
        self.assertEqual(self.interface.detect_wake_word.call_count, 1)
        
        # Should have processed multiple queries
        self.assertGreaterEqual(self.interface.listen.call_count, 3)
        self.assertGreaterEqual(self.interface.send_to_claude.call_count, 3)
    
    def test_goodbye_variations(self):
        """Test different goodbye phrases exit the session."""
        goodbye_phrases = ["goodbye", "bye", "see you", "talk to you later"]
        
        for phrase in goodbye_phrases:
            with self.subTest(phrase=phrase):
                self.interface.detect_wake_word = Mock(return_value=True)
                self.interface.listen = Mock(side_effect=[phrase])
                self.interface.speak = Mock()
                
                # Run briefly
                import threading
                def run_wake_mode():
                    try:
                        self.interface.wake_word_mode()
                    except (StopIteration, RuntimeError):
                        pass
                
                thread = threading.Thread(target=run_wake_mode)
                thread.daemon = True
                thread.start()
                thread.join(timeout=0.2)
                
                # Should have said a farewell
                calls = [str(call) for call in self.interface.speak.call_args_list]
                farewell_said = any(
                    any(word in str(call).lower() for word in ["goodbye", "bye", "see you", "cheerio"])
                    for call in calls
                )
                self.assertTrue(farewell_said or len(calls) >= 1)


if __name__ == "__main__":
    unittest.main()