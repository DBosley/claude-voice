.PHONY: help install install-dev install-vad run chat ask wake wake-verbose chat-verbose ask-verbose lint format check test clean

help:
	@echo "Available commands:"
	@echo "  make run           - Run voice assistant in wake mode"
	@echo "  make chat          - Run in conversation mode"
	@echo "  make ask           - Run in single question mode"
	@echo "  make wake          - Run in wake word mode (default)"
	@echo "  make wake-verbose  - Run wake mode with verbose logging"
	@echo "  make chat-verbose  - Run chat mode with verbose logging"
	@echo "  make ask-verbose   - Run ask mode with verbose logging"
	@echo "  make install       - Install base dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make install-vad   - Install VAD dependencies"
	@echo "  make lint          - Run linting (ruff check and fix)"
	@echo "  make format        - Format code with black"
	@echo "  make check         - Run all checks without modifying files"
	@echo "  make test          - Run tests"
	@echo "  make clean         - Clean up cache files"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,tts,vad]"
	pre-commit install

install-vad:
	./install-vad.sh

lint:
	ruff check --fix .
	ruff format .

format:
	black .

run: wake

chat:
	python claude_voice.py chat $(ARGS)

ask:
	python claude_voice.py ask $(ARGS)

wake:
	python claude_voice.py wake $(ARGS)

wake-verbose:
	python claude_voice.py wake --verbose

chat-verbose:
	python claude_voice.py chat --verbose

ask-verbose:
	python claude_voice.py ask --verbose

check:
	ruff check .
	black --check .
	mypy voice_assistant/

test:
	.venv/bin/pytest tests/ -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete