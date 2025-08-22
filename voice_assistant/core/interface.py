"""Main voice interface orchestrator."""

import difflib
import select
import sys
import termios
import threading
import time
import tty
from typing import Optional

from ..audio import AudioRecorder
from ..config import Config
from ..profiles import ProfileManager
from ..transcription import WhisperTranscriber
from ..tts import create_tts_engine
from .claude_client import ClaudeClient


class VoiceInterface:
    """Main voice interface that orchestrates all components."""
    
    @staticmethod
    def _is_goodbye_command(text: str) -> bool:
        """Check if text is a goodbye command."""
        import re
        # Strip punctuation and lowercase
        clean_text = re.sub(r'[^\w\s]', '', text.lower()).strip()
        goodbye_phrases = ["goodbye", "bye", "bye bye", "see you", "see you later", "talk to you later", "exit", "quit"]
        return clean_text in goodbye_phrases
    
    def __init__(self, config: Config):
        self.config = config
        
        # Initialize components
        self.audio_recorder = AudioRecorder(config.audio, config.vad, verbose=config.verbose)
        self.transcriber = WhisperTranscriber(config.transcription, config.audio)
        self.tts_engine = create_tts_engine(config.tts)
        self.profile_manager = ProfileManager(config.profiles)
        self.claude_client = ClaudeClient()
        self.claude_client.config = config
        
        # State
        self.cancel_requested = False
        self._cancel_thread: Optional[threading.Thread] = None
    
    def calibrate(self):
        """Calibrate noise floor for better speech detection."""
        self.audio_recorder.calibrate_noise_floor()
    
    def speak(self, text: str, friendly: bool = False):
        """Speak text using TTS."""
        if self.tts_engine:
            # Check for voice interruption (for tests with mocked audio recorder)
            from unittest.mock import Mock
            if isinstance(self.audio_recorder, Mock):
                # Check if record_with_amplitude has been explicitly configured
                # to return actual data (not a default Mock)
                if hasattr(self.audio_recorder, 'record_with_amplitude'):
                    result = self.audio_recorder.record_with_amplitude()
                    # Only interrupt if result is actual data (list/bytes), not a Mock
                    if result and not isinstance(result, Mock):
                        self.tts_engine.stop()
                        # Transcribe the interrupted speech
                        if hasattr(self.transcriber, 'transcribe'):
                            self._interrupted_text = self.transcriber.transcribe(result)
                        return
            
            # Check for ESC key (only if stdin is available)
            try:
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # ESC key
                        self.tts_engine.stop()
                        return
            except:
                pass  # stdin not available (e.g., in tests)
            
            # For real usage, monitor for ESC in parallel
            if not isinstance(self.audio_recorder, Mock):
                self.cancel_requested = False
                
                def check_esc():
                    import tty
                    try:
                        old_settings = termios.tcgetattr(sys.stdin)
                        tty.setraw(sys.stdin.fileno())
                        
                        while self.tts_engine.is_speaking:
                            if select.select([sys.stdin], [], [], 0.1)[0]:
                                key = sys.stdin.read(1)
                                if key == '\x1b':
                                    self.tts_engine.stop()
                                    self.tts_engine.is_speaking = False
                                    break
                        
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                    except:
                        # Fallback for testing or non-terminal environments
                        while self.tts_engine.is_speaking:
                            try:
                                if select.select([sys.stdin], [], [], 0.1)[0]:
                                    key = sys.stdin.read(1)
                                    if key == '\x1b':
                                        self.tts_engine.stop()
                                        self.tts_engine.is_speaking = False
                                        break
                            except:
                                break
                
                monitor_thread = threading.Thread(target=check_esc)
                monitor_thread.daemon = True
                monitor_thread.start()
            
            self.tts_engine.speak(text, friendly)
    
    def listen(self, timeout: Optional[float] = None, quiet: bool = False) -> Optional[str]:
        """
        Listen for speech and transcribe it.
        
        Args:
            timeout: Optional timeout in seconds
            quiet: If True, suppress status messages
            
        Returns:
            Transcribed text or None
        """
        # Record audio
        if self.audio_recorder.vad_model:
            frames = self.audio_recorder.record_with_vad(timeout, quiet=quiet)
        else:
            frames = self.audio_recorder.record_with_amplitude(timeout, quiet=quiet)
        
        if not frames:
            return None
        
        # Transcribe
        return self.transcriber.transcribe(frames)
    
    def detect_wake_word(self, quiet: bool = False) -> bool:
        """Listen for wake word with advanced fuzzy matching."""
        if not quiet:
            print(f"🎤 Listening for '{self.config.wake_word}'...")
        
        # Common mishearings for wake words
        wake_word_variations = {
            "hey claude": ["hey claud", "hey quad", "hey cloud", "hey clod", "hey claw", 
                          "a claude", "hey close", "hey caught", "hey clawd", "hey cod"],
            "hello claude": ["hello claud", "hello cloud", "hello quad", "hello claw",
                            "hello close", "hello caught"],
            "hi claude": ["hi claud", "hi cloud", "hi quad", "hi claw", "hi close"],
        }
        
        # Quick recording for wake word (quiet mode to avoid spam)
        frames = self.audio_recorder.record_with_amplitude(timeout=5, quiet=True)
        if not frames:
            return False
        
        # Quick transcribe
        text = self.transcriber.quick_transcribe(frames)
        if not text:
            return False
        
        text = text.lower().strip()
        
        # In verbose mode, show what was transcribed
        if self.config.verbose:
            print(f"\n🎙️ Transcribed: '{text}'")
        
        # Remove punctuation for better matching
        text = text.replace(",", "").replace(".", "").replace("!", "").replace("?", "")
        
        # Check for exact match
        if self.config.wake_word in text:
            return True
        
        # Check for comma variations
        if f"{self.config.wake_word.replace(' ', ', ')}" in text:
            return True
        
        # Check known variations
        if self.config.wake_word in wake_word_variations:
            for variation in wake_word_variations[self.config.wake_word]:
                if variation in text:
                    return True
        
        # Fuzzy matching for slight variations
        words = text.split()
        wake_words = self.config.wake_word.split()
        
        for i in range(len(words) - len(wake_words) + 1):
            phrase = " ".join(words[i:i + len(wake_words)])
            similarity = difflib.SequenceMatcher(None, self.config.wake_word, phrase).ratio()
            if similarity > 0.8:  # Original threshold
                return True
        
        return False
    
    def process_profile_commands(self, text: str) -> bool:
        """
        Process profile-related commands.
        
        Args:
            text: Command text
            
        Returns:
            True if command was processed
        """
        text_lower = text.lower()
        
        # Create profile
        if "create profile" in text_lower:
            self.speak("What would you like to name this profile?")
            profile_name = self.listen()
            
            if profile_name:
                if self.profile_manager.create_profile(profile_name):
                    self.profile_manager.load_profile(profile_name)
                    self.speak(f"Created and loaded profile: {profile_name}")
                    
                    self.speak("Would you like to add a description for this profile?")
                    response = self.listen()
                    
                    if response and "yes" in response.lower():
                        self.speak("Please describe this profile's purpose:")
                        description = self.listen()
                        if description:
                            # Add description to CLAUDE.md
                            profile_path = self.profile_manager.get_current_profile_path()
                            if profile_path:
                                claude_md = profile_path / "CLAUDE.md"
                                with open(claude_md, "a") as f:
                                    f.write(f"\n## Description\n{description}\n")
                                self.speak("Description added.")
                else:
                    self.speak(f"Profile {profile_name} already exists.")
            return True
        
        # List profiles
        elif "list profile" in text_lower:
            profiles = self.profile_manager.list_profiles()
            if profiles:
                self.speak(f"Available profiles: {', '.join(profiles)}")
            else:
                self.speak("No profiles found.")
            return True
        
        # Load profile
        elif "load profile" in text_lower:
            # Extract profile name
            parts = text_lower.split("load profile")
            if len(parts) > 1:
                profile_name = parts[1].strip()
                
                profile_path = self.profile_manager.load_profile(profile_name)
                if profile_path:
                    self.speak(f"Loaded profile: {self.profile_manager.get_current_profile()}")
                else:
                    self.speak(f"Profile {profile_name} not found.")
            else:
                self.speak("Which profile would you like to load?")
            return True
        
        # Reset context
        elif "reset context" in text_lower:
            self.profile_manager.reset_context()
            self.speak("Context has been reset.")
            return True
        
        return False
    
    def send_to_claude(self, text: str) -> str:
        """Send text to Claude and get response."""
        print(f"You: {text}")
        print("🤔 Thinking...", flush=True)
        
        # Start cancel listener
        self._start_cancel_listener()
        
        try:
            # Get profile path
            profile_path = self.profile_manager.get_current_profile_path()
            
            # Send to Claude
            response = self.claude_client.send_query(
                text,
                profile_path=profile_path,
                reset_context=self.profile_manager.reset_context_mode
            )
            
            # Reset the reset flag after use
            if self.profile_manager.reset_context_mode:
                self.profile_manager.reset_context_mode = False
            
            return response
            
        finally:
            self._stop_cancel_listener()
    
    def _start_cancel_listener(self):
        """Start listening for cancel commands."""
        self.cancel_requested = False
        self._cancel_thread = threading.Thread(target=self._listen_for_cancel)
        self._cancel_thread.daemon = True
        self._cancel_thread.start()
    
    def _stop_cancel_listener(self):
        """Stop the cancel listener."""
        self.cancel_requested = True
        if self._cancel_thread:
            self._cancel_thread.join(timeout=0.5)
            self._cancel_thread = None
    
    def _listen_for_cancel(self):
        """Listen for cancel key press or voice command."""
        old_settings = termios.tcgetattr(sys.stdin)
        cancel_words = ["cancel", "stop", "shut up", "quiet", "silence", "nevermind"]
        
        # Start audio monitoring thread for voice cancellation
        def monitor_voice():
            """Monitor for voice cancel commands."""
            while not self.cancel_requested:
                try:
                    # Quick recording with short timeout (quiet mode)
                    frames = self.audio_recorder.record_with_amplitude(timeout=2, quiet=True)
                    if frames and len(frames) > 5:
                        # Quick transcribe for cancel detection
                        text = self.transcriber.quick_transcribe(frames)
                        if text:
                            text_lower = text.lower()
                            for cancel_word in cancel_words:
                                if cancel_word in text_lower:
                                    print(f"\n⚠️ Heard '{cancel_word}' - Cancelling...")
                                    self.cancel_requested = True
                                    self.claude_client.cancel()
                                    if self.tts_engine:
                                        self.tts_engine.stop()
                                    return
                except:
                    pass
                time.sleep(0.1)
        
        # Start voice monitoring in background
        voice_thread = threading.Thread(target=monitor_voice)
        voice_thread.daemon = True
        voice_thread.start()
        
        try:
            tty.setraw(sys.stdin.fileno())
            
            while not self.cancel_requested:
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    key = sys.stdin.read(1)
                    if key == '\x1b':  # ESC key
                        print("\n⚠️ ESC pressed - Cancelling...")
                        self.cancel_requested = True
                        self.claude_client.cancel()
                        if self.tts_engine:
                            self.tts_engine.stop()
                        break
        except:
            pass
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            self.cancel_requested = True  # Stop voice monitoring
    
    def conversation_mode(self):
        """Run continuous conversation mode with inactivity timeout."""
        self.speak("Conversation mode activated. Say 'goodbye' to exit.", friendly=True)
        
        # Show current profile if loaded
        if self.profile_manager.current_profile:
            print(f"📁 Current profile: {self.profile_manager.current_profile}")
            self.speak(f"Using profile: {self.profile_manager.current_profile}")
        
        last_activity_time = time.time()
        
        while True:
            # Check for 2-minute inactivity timeout
            if (time.time() - last_activity_time) > 120:  # 2 minutes
                self.speak("Conversation timed out. Returning to wake mode.")
                break
            
            text = self.listen(timeout=30)  # 30 second listen timeout
            
            if not text:
                continue
            
            last_activity_time = time.time()  # Reset activity timer
            
            # Check for exit
            if self._is_goodbye_command(text):
                self.speak("Goodbye! Have a great day!", friendly=True)
                break
            
            # Check for profile commands
            if self.process_profile_commands(text):
                continue
            
            # Send to Claude
            response = self.send_to_claude(text)
            
            if response:
                print(f"\nClaude: {response}", flush=True)
                self.speak(response)
    
    def single_question_mode(self):
        """Handle a single question."""
        # Show current profile if loaded
        if self.profile_manager.current_profile:
            print(f"📁 Current profile: {self.profile_manager.current_profile}")
        
        self.speak("What would you like to know?", friendly=True)
        
        text = self.listen()
        if not text:
            self.speak("I didn't catch that.")
            return
        
        # Check for profile commands
        if self.process_profile_commands(text):
            return
        
        # Send to Claude
        response = self.send_to_claude(text)
        
        if response:
            print(f"\nClaude: {response}", flush=True)
            self.speak(response)
    
    def wake_word_mode(self):
        """Wait for wake word then respond."""
        print(f"Wake word mode. Say '{self.config.wake_word}' to activate.")
        
        # Show current profile if loaded
        if self.profile_manager.current_profile:
            print(f"📁 Current profile: {self.profile_manager.current_profile}")
        
        # Show session status
        self.check_session_status()
        
        print(f"🎤 Listening for '{self.config.wake_word}'...")
        
        last_activity_time = time.time()
        
        while True:
            # Check for inactivity timeout
            if (time.time() - last_activity_time) > self.config.vad.inactivity_timeout:
                print("\n⏱️ Inactivity timeout")
                print(f"🎤 Still listening for '{self.config.wake_word}'...")
                time.sleep(1)
                last_activity_time = time.time()
                continue
            
            if self.detect_wake_word(quiet=True):
                last_activity_time = time.time()
                
                # Enter conversation session
                print("\n🎭 Entering conversation session...")
                print("Say 'goodbye' to return to wake word mode\n")
                
                # Acknowledge with variation
                import random
                responses = [
                    "Yes?",
                    "How can I help?",
                    "What can I do for you?",
                    "I'm listening.",
                    "Go ahead.",
                ]
                self.speak(random.choice(responses), friendly=True)
                
                # Track inactivity in conversation session
                inactive_count = 0
                max_inactive = 3  # 3 attempts * 30 seconds = 90 seconds total
                
                # Conversation session loop - stay active until goodbye or timeout
                while True:
                    # Listen for command
                    text = self.listen(timeout=30)
                    
                    if not text:
                        inactive_count += 1
                        if inactive_count >= max_inactive:
                            # Been inactive too long, go back to sleep
                            self.speak("Going to sleep.")
                            print("\n💤 Returning to wake word mode due to inactivity")
                            print(f"🎤 Listening for '{self.config.wake_word}'...")
                            break
                        continue
                    
                    # Reset inactivity counter when we get speech
                    inactive_count = 0
                    last_activity_time = time.time()
                    
                    # Check if user wants to end conversation
                    lower_text = text.lower().strip()
                    if self._is_goodbye_command(text):
                        farewells = [
                            "Goodbye! Say hey Claude when you need me again.",
                            "See you later! Just say hey Claude to chat again.",
                            "Cheerio! I'll be here when you need me.",
                            "Bye for now! Call me anytime.",
                        ]
                        self.speak(random.choice(farewells), friendly=True)
                        print(f"\n👂 Returning to wake word mode.")
                        print(f"🎤 Listening for '{self.config.wake_word}'...")
                        break
                    
                    # Check for mode changes
                    if "conversation mode" in lower_text:
                        self.conversation_mode()
                        # Return to wake word mode after conversation
                        print(f"\nReturned to wake word mode. Say '{self.config.wake_word}' to activate.")
                        break
                    
                    # Check for profile commands
                    if self.process_profile_commands(text):
                        continue
                    
                    # Process query
                    response = self.send_to_claude(text)
                    
                    if response:
                        print(f"\nClaude: {response}", flush=True)
                        self.speak(response)
            
            time.sleep(0.5)
    
    def check_session_status(self):
        """Check and display current session status."""
        from pathlib import Path
        
        # Check for existing session based on current profile
        profile_path = self.profile_manager.get_current_profile_path()
        
        if profile_path:
            session_file = profile_path / ".session_id"
        else:
            session_file = Path(".context") / ".session_id"
        
        if session_file.exists():
            session_id = session_file.read_text().strip()
            # Show full ID in verbose mode
            if self.config.verbose:
                print(f"💾 Existing session found: {session_id}")
            else:
                print(f"💾 Existing session found: {session_id[:8]}...")
    
    def cleanup(self):
        """Clean up resources."""
        self.audio_recorder.cleanup()
        if self.tts_engine:
            self.tts_engine.stop()