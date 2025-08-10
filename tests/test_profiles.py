"""Tests for profile management."""

import pytest
import tempfile
from pathlib import Path

from voice_assistant.profiles import ProfileManager
from voice_assistant.config import ProfileConfig


class TestProfileManager:
    """Test profile management functionality."""
    
    @pytest.fixture
    def temp_context_dir(self):
        """Create temporary context directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def profile_manager(self, temp_context_dir):
        """Create profile manager with temp directory."""
        config = ProfileConfig(
            context_dir=temp_context_dir,
            profile_state_file=temp_context_dir / "state.json"
        )
        return ProfileManager(config)
    
    def test_create_profile(self, profile_manager):
        """Test profile creation."""
        result = profile_manager.create_profile("test_profile")
        assert result == True
        
        # Check profile exists
        profile_dir = profile_manager.config.context_dir / "test_profile"
        assert profile_dir.exists()
        assert (profile_dir / "CLAUDE.md").exists()
        
        # Check duplicate creation fails
        result = profile_manager.create_profile("test_profile")
        assert result == False
    
    def test_sanitize_name(self, profile_manager):
        """Test profile name sanitization."""
        name = profile_manager._sanitize_name("Test Profile!")
        assert name == "test_profile"
        
        name = profile_manager._sanitize_name("My-Special Profile")
        assert name == "my_special_profile"
        
        name = profile_manager._sanitize_name("Profile@#$%123")
        assert name == "profile123"
    
    def test_list_profiles(self, profile_manager):
        """Test listing profiles."""
        # Initially empty
        profiles = profile_manager.list_profiles()
        assert profiles == []
        
        # Create some profiles
        profile_manager.create_profile("profile1")
        profile_manager.create_profile("profile2")
        
        profiles = profile_manager.list_profiles()
        assert len(profiles) == 2
        assert "profile1" in profiles
        assert "profile2" in profiles
    
    def test_load_profile(self, profile_manager):
        """Test loading a profile."""
        # Create profile
        profile_manager.create_profile("test_profile")
        
        # Load it
        profile_path = profile_manager.load_profile("test_profile")
        assert profile_path is not None
        assert profile_path.name == "test_profile"
        assert profile_manager.current_profile == "test_profile"
        
        # Try loading non-existent profile
        profile_path = profile_manager.load_profile("nonexistent")
        assert profile_path is None
    
    def test_reset_context(self, profile_manager):
        """Test context reset."""
        # Load a profile
        profile_manager.create_profile("test_profile")
        profile_manager.load_profile("test_profile")
        assert profile_manager.current_profile == "test_profile"
        
        # Reset
        profile_manager.reset_context()
        assert profile_manager.current_profile is None
        assert profile_manager.reset_context_mode == True
    
    def test_get_profile_info(self, profile_manager):
        """Test getting profile information."""
        # Create profile
        profile_manager.create_profile("test_profile")
        
        # Get info
        info = profile_manager.get_profile_info("test_profile")
        assert info is not None
        assert info["name"] == "test_profile"
        assert info["has_claude_md"] == True
        assert "path" in info
        
        # Non-existent profile
        info = profile_manager.get_profile_info("nonexistent")
        assert info is None
    
    def test_profile_persistence(self, profile_manager):
        """Test profile state persistence."""
        # Create and load profile
        profile_manager.create_profile("persistent")
        profile_manager.load_profile("persistent")
        
        # Create new manager with same config
        new_manager = ProfileManager(profile_manager.config)
        
        # Should remember last profile
        assert new_manager.current_profile == "persistent"