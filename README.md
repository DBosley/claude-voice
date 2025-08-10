# Claude Voice Assistant

A sophisticated voice-controlled interface for Claude with natural text-to-speech, advanced voice activity detection, and profile management capabilities.

## Features

### 🎤 Voice Interface
- **Whisper Speech Recognition**: Accurate transcription using OpenAI Whisper (tiny to large models)
- **Dual TTS Engines**: 
  - Coqui TTS: Natural British voices with sentence streaming
  - Piper TTS: Fast, lightweight speech synthesis
- **Voice Activity Detection**: Silero VAD for accurate speech detection
- **Wake Word Detection**: Configurable wake word with fuzzy matching

### 🎯 Interaction Modes
- **Wake Mode**: Activated by wake word ("Hey Claude" by default)
- **Chat Mode**: Continuous conversation with 2-minute inactivity timeout
- **Ask Mode**: Single question/answer interaction

### 👤 Profile System
- Create and manage multiple conversation contexts
- Each profile maintains its own CLAUDE.md instructions and session state
- Voice commands for profile management
- Persistent sessions with automatic UUID-based resumption

## Installation

### Prerequisites
- Python 3.10+
- PipeWire or PulseAudio
- Claude CLI installed and configured

### Quick Setup

```bash
# Clone repository
git clone <repository-url>
cd claude-voice

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Optional: Install VAD for better speech detection
pip install silero-vad torch torchaudio

# Optional: Install development dependencies
make install-dev
```

## Usage

### Running the Assistant

```bash
# Use the launcher script (recommended)
./claude-voice wake    # Wake word mode
./claude-voice chat    # Conversation mode
./claude-voice ask     # Single question mode

# Or run directly
python claude_voice.py wake
```

### Command Line Options

```bash
# Mode selection (positional argument)
{chat,ask,wake}                          # Interaction mode (default: wake)

# Audio configuration
--model {tiny,base,small,medium,large}  # Whisper model size (default: base)
--sample-rate {16000,48000}              # Audio sample rate in Hz (default: 16000)
--silence-threshold INT                  # Amplitude threshold for silence detection (default: 1000)
--calibrate                              # Calibrate noise floor before starting

# Voice configuration
--wake-word "your phrase"                # Custom wake word (default: "hey claude")
--tts-engine {auto,coqui,piper}         # TTS engine selection (default: auto)
--voice NAME                             # TTS voice selection:
                                         #   british_male, british_female (Coqui)
                                         #   alan, cori (Piper)
                                         #   p258, p287 (Coqui raw models)
--speech-rate FLOAT                      # Speech rate: 0.5=fast, 1.5=slow (default: 1.1)

# Debugging
--verbose                                # Enable verbose logging for debugging
```

### Voice Commands

Available in all modes:
- **"Create profile"**: Interactive profile creation
- **"Load profile [name]"**: Switch to a specific profile
- **"List profiles"**: Show available profiles
- **"Reset context"**: Clear current profile
- **"Cancel"**: Stop current operation
- **"Goodbye"** or **"Exit"**: End session

## Profile Management

Profiles allow you to maintain separate conversation contexts for different use cases.

### Profile Structure
```
.context/
├── profile_name/
│   └── CLAUDE.md    # Profile-specific instructions
├── another_profile/
│   └── CLAUDE.md
└── .claude/
    └── settings.json  # Security settings
```

### Creating a Profile
1. Say "create profile" when prompted
2. Provide a name for the profile
3. Describe what the profile should help with
4. The assistant will create a tailored CLAUDE.md

### Using Profiles
- Profiles maintain session continuity using Claude's `--resume` flag
- Each profile gets its own UUID for session management
- Context automatically switches when loading profiles

## Technical Details

### Audio Configuration
- **Sample Rate**: Configurable (16kHz default, 48kHz supported)
- **Format**: 16-bit PCM, mono
- **Chunk Size**: 512 samples for VAD, 1024 for amplitude detection

### Voice Activity Detection
- **Start Threshold**: 0.85 (high confidence to start)
- **Continue Threshold**: 0.5 (lower to maintain)
- **Silence Duration**: 2 seconds to end recording
- **Pre-buffer**: 10 chunks (~320ms) to capture speech onset

### TTS Features
- **Sentence Streaming**: Parallel processing for faster response
- **Smart Splitting**: Breaks on punctuation, avoids fragments
- **Voice Options**:
  - Coqui: p258 (male), p287 (female) British voices
  - Piper: alan (male), cori (female) voices

## Development

### Running Tests
```bash
make test              # Run all tests
make test-verbose      # Run with verbose output
```

### Code Quality
```bash
make lint              # Run ruff linting with fixes
make format            # Format with black
make check             # Check without modifying
make clean             # Clean cache files
```

### Project Structure
```
claude-voice/
├── claude_voice.py              # Main entry point
├── voice_assistant/             # Package modules
│   ├── audio/                   # Audio recording/playback
│   ├── config/                  # Configuration management
│   ├── core/                    # Core interfaces
│   ├── profiles/                # Profile management
│   ├── transcription/           # Whisper integration
│   └── tts/                     # TTS engines
├── tests/                       # Test suite
├── .context/                    # User profiles (gitignored)
└── Makefile                     # Development commands
```

## Troubleshooting

### No Audio Input
- Check default audio device: `pactl info | grep "Default Source"`
- Ensure microphone permissions are granted
- Try calibration mode: `--calibrate`

### Poor Transcription
- Use larger Whisper model: `--model medium`
- Ensure clear audio input without background noise
- Check microphone positioning

### TTS Issues
- Coqui TTS requires more resources but sounds natural
- Piper TTS is faster but more robotic
- Try switching engines: `--tts-engine piper`

### Profile Issues
- Profiles are case-insensitive and punctuation is removed
- Check `.context/` directory for profile folders
- Ensure Claude CLI is properly configured

## Security

The assistant runs in a sandboxed environment:
- Claude operations restricted to `.context/` directory
- No system command execution
- No network access from sandbox
- Settings enforced via `.context/.claude/settings.json`

## Contributing

- Follow existing code patterns
- Run tests before submitting: `make test`
- Use linting tools: `make lint`
- Update documentation when adding features

## License

[Your License Here]

## Acknowledgments

- OpenAI Whisper for speech recognition
- Silero team for VAD model
- Coqui TTS for natural voices
- Piper TTS for fast synthesis
- Claude by Anthropic