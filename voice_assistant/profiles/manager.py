"""Profile management for different conversation contexts."""

import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..config import ProfileConfig


class ProfileManager:
    """Manages conversation profiles and contexts."""
    
    def __init__(self, config: ProfileConfig):
        self.config = config
        self.current_profile: Optional[str] = None
        self.reset_context_mode = False
        self.session_id: Optional[str] = None
        self.session_started: Optional[datetime] = None
        
        # Ensure context directory exists
        self.config.context_dir.mkdir(parents=True, exist_ok=True)
        
        # Load last used profile and session
        self._load_last_profile()
    
    def _load_last_profile(self):
        """Load the last used profile and session from state file."""
        if self.config.profile_state_file.exists():
            try:
                with open(self.config.profile_state_file) as f:
                    state = json.load(f)
                    profile_name = state.get("last_profile")
                    if profile_name and self._profile_exists(profile_name):
                        self.current_profile = profile_name
                    
                    # Load session info
                    self.session_id = state.get("session_id")
                    session_started = state.get("session_started")
                    if session_started:
                        self.session_started = datetime.fromisoformat(session_started)
                        
                        # Check if this is a resume (within 30 minutes)
                        if self.session_started:
                            time_diff = datetime.now() - self.session_started
                            if time_diff.total_seconds() < 1800:  # 30 minutes
                                # Don't print session info - let Claude CLI handle this
                                pass
                            else:
                                self._start_new_session()
                    else:
                        self._start_new_session()
            except Exception:
                self._start_new_session()
    
    def _save_last_profile(self):
        """Save the current profile and session to state file."""
        self.config.profile_state_file.parent.mkdir(parents=True, exist_ok=True)
        
        state = {
            "last_profile": self.current_profile,
            "session_id": self.session_id,
            "session_started": self.session_started.isoformat() if self.session_started else None
        }
        
        with open(self.config.profile_state_file, "w") as f:
            json.dump(state, f, indent=2)
    
    def _start_new_session(self):
        """Start a new session with UUID."""
        self.session_id = str(uuid.uuid4())
        self.session_started = datetime.now()
        # Don't print session ID - let Claude CLI handle this
    
    def _profile_exists(self, profile_name: str) -> bool:
        """Check if a profile exists."""
        profile_dir = self.config.context_dir / self._sanitize_name(profile_name)
        return profile_dir.exists() and profile_dir.is_dir()
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize profile name for filesystem."""
        # Remove punctuation and replace spaces with underscores
        name = re.sub(r'[^\w\s-]', '', name.lower())
        name = re.sub(r'[-\s]+', '_', name)
        return name.strip('_')
    
    def create_profile(self, profile_name: str) -> bool:
        """
        Create a new profile.
        
        Args:
            profile_name: Name of the profile to create
            
        Returns:
            True if created successfully
        """
        sanitized_name = self._sanitize_name(profile_name)
        profile_dir = self.config.context_dir / sanitized_name
        
        if profile_dir.exists():
            return False
        
        # Create profile directory
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        # Create CLAUDE.md with initial content
        claude_md = profile_dir / "CLAUDE.md"
        initial_content = f"""# Profile: {profile_name}

## Context
This is a specialized conversation profile for {profile_name}.

## Instructions
- Maintain context specific to this profile
- Remember previous conversations in this profile
- Adapt responses to the profile's purpose

## Notes
Created: {Path.cwd()}
"""
        
        with open(claude_md, "w") as f:
            f.write(initial_content)
        
        return True
    
    def list_profiles(self) -> List[str]:
        """
        List all available profiles.
        
        Returns:
            List of profile names
        """
        profiles = []
        
        if not self.config.context_dir.exists():
            return profiles
        
        for item in self.config.context_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                # Check if it has a CLAUDE.md file
                if (item / "CLAUDE.md").exists():
                    profiles.append(item.name)
        
        return sorted(profiles)
    
    def load_profile(self, profile_name: str) -> Optional[Path]:
        """
        Load a profile and set it as current with advanced fuzzy matching.
        
        Args:
            profile_name: Name of the profile to load
            
        Returns:
            Path to the profile directory if successful
        """
        # Try multiple name resolution strategies
        strategies = [
            # 1. Try exact sanitized name
            lambda n: self._sanitize_name(n),
            # 2. Try with underscores for spaces
            lambda n: n.lower().replace(' ', '_').replace(',', '').replace('.', ''),
            # 3. Try without any spaces
            lambda n: n.lower().replace(' ', '').replace(',', '').replace('.', ''),
            # 4. Try with dashes for spaces
            lambda n: n.lower().replace(' ', '-').replace(',', '').replace('.', ''),
            # 5. Try as-is (already sanitized by user)
            lambda n: n.lower(),
        ]
        
        profile_dir = None
        for strategy in strategies:
            test_name = strategy(profile_name)
            test_dir = self.config.context_dir / test_name
            
            if test_dir.exists() and test_dir.is_dir():
                profile_dir = test_dir
                print(f"✓ Found profile '{test_name}' using strategy")
                break
        
        # If still not found, try fuzzy matching against existing profiles
        if not profile_dir or not profile_dir.exists():
            profiles = self.list_profiles()
            sanitized_name = self._sanitize_name(profile_name)
            
            for p in profiles:
                if sanitized_name in p or p in sanitized_name:
                    profile_dir = self.config.context_dir / p
                    print(f"✓ Found profile '{p}' via fuzzy match")
                    break
            else:
                print(f"✗ Could not find profile matching '{profile_name}'")
                print(f"  Available profiles: {', '.join(profiles) if profiles else 'none'}")
                return None
        
        if not profile_dir.exists():
            return None
        
        self.current_profile = profile_dir.name
        self.reset_context_mode = False
        
        # Don't start new session - let Claude CLI handle sessions
        # Just save the profile state
        self._save_last_profile()
        
        return profile_dir
    
    def get_current_profile(self) -> Optional[str]:
        """Get the name of the current profile."""
        return self.current_profile
    
    def get_current_profile_path(self) -> Optional[Path]:
        """Get the path to the current profile directory."""
        if self.current_profile:
            return self.config.context_dir / self.current_profile
        return None
    
    def reset_context(self):
        """Reset the current conversation but keep the profile loaded."""
        # Keep the current profile loaded
        # Just start a new session to reset the conversation
        self._start_new_session()
        self.reset_context_mode = True
        self._save_last_profile()
    
    def get_profile_info(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a profile.
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Dictionary with profile information
        """
        sanitized_name = self._sanitize_name(profile_name)
        profile_dir = self.config.context_dir / sanitized_name
        
        if not profile_dir.exists():
            return None
        
        claude_md = profile_dir / "CLAUDE.md"
        
        info = {
            "name": profile_name,
            "path": str(profile_dir),
            "has_claude_md": claude_md.exists(),
        }
        
        if claude_md.exists():
            try:
                with open(claude_md) as f:
                    content = f.read()
                    # Extract first few lines as description
                    lines = content.split("\n")
                    info["description"] = "\n".join(lines[:5])
            except:
                pass
        
        return info