#!/usr/bin/env python3
"""
Claude Voice Assistant - Refactored modular version.

A voice-controlled interface for Claude with natural text-to-speech,
advanced voice activity detection, and profile management.
"""

import argparse
import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent))

from voice_assistant.config import Config
from voice_assistant.core import VoiceInterface


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Claude Voice Interface with natural TTS"
    )
    
    # Mode selection
    parser.add_argument(
        "mode",
        choices=["chat", "ask", "wake"],
        default="wake",
        nargs="?",
        help="Interaction mode (default: wake)",
    )
    
    # Model configuration
    parser.add_argument(
        "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Whisper model size (default: base)",
    )
    
    # Wake word
    parser.add_argument(
        "--wake-word",
        default="hey claude",
        help="Wake word to activate (default: 'hey claude')",
    )
    
    # Voice selection
    parser.add_argument(
        "--voice",
        choices=["british_male", "british_female", "alan", "cori", "p258", "p287"],
        default="british_male",
        help="TTS voice selection",
    )
    
    # TTS engine
    parser.add_argument(
        "--tts-engine",
        choices=["auto", "coqui", "piper"],
        default="auto",
        help="TTS engine to use (default: auto)",
    )
    
    # Speech rate
    parser.add_argument(
        "--speech-rate",
        type=float,
        default=1.1,
        help="Speech rate (0.5=fast, 1.5=slow, default: 1.1)",
    )
    
    # Calibration
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Calibrate noise floor before starting",
    )
    
    # Silence threshold
    parser.add_argument(
        "--silence-threshold",
        type=int,
        default=1000,
        help="Silence threshold for amplitude detection",
    )
    
    # Sample rate
    parser.add_argument(
        "--sample-rate",
        type=int,
        choices=[16000, 48000],
        default=16000,
        help="Audio sample rate in Hz (default: 16000, use 48000 for some headsets)",
    )
    
    # Verbose mode
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging for debugging",
    )
    
    args = parser.parse_args()
    
    # Create configuration
    config = Config.from_args(
        model_size=args.model,
        wake_word=args.wake_word,
        voice=args.voice,
        tts_engine=args.tts_engine,
        speech_rate=args.speech_rate,
        silence_threshold=args.silence_threshold,
        sample_rate=args.sample_rate,
        verbose=args.verbose,
    )
    
    # Create interface
    interface = VoiceInterface(config)
    
    try:
        # Calibrate if requested
        if args.calibrate:
            interface.calibrate()
        
        # Run selected mode
        if args.mode == "chat":
            interface.conversation_mode()
        elif args.mode == "ask":
            interface.single_question_mode()
        else:  # wake
            interface.wake_word_mode()
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    finally:
        interface.cleanup()


if __name__ == "__main__":
    main()