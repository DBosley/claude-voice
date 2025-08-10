# Claude Voice Assistant

Voice-controlled assistant using Whisper STT and dual TTS engines (Coqui/Piper).

## Essential Commands

**Testing:**
```bash
make test  # ALWAYS use this instead of pytest directly
```

**Running:**
```bash
./claude-voice wake   # Wake word mode
./claude-voice chat   # Conversation mode  
./claude-voice ask    # Single question mode
```

**Development:**
```bash
make lint    # Run ruff linting
make format  # Format with black
make check   # Check without modifying
```

**Rules to follow:**
- ALWAYS update the README.md when adding new options to the claude-voice CLI
- ALWAYS update the CLAUDE.md file when adding new Makefile commands
- Wrap all functionality in unit tests when possible. Always follow TDD

## Project Structure
- `claude_voice.py` - Main entry point (NOT claude-voice.py)
- `voice_assistant/` - Package with modular components
- `.context/` - Sandboxed profiles directory
- `tests/` - Test suite

## Key Implementation Notes
- Profile system stores contexts in `.context/[profile_name]/CLAUDE.md`
- Claude CLI runs with `--resume [uuid]` for profile continuity
- VAD uses Silero with 0.85/0.5 thresholds
- TTS supports sentence streaming for faster response
- 2-minute inactivity timeout in chat mode

## Security
All Claude operations sandboxed to `.context/` via settings.json - no system access.