"""Claude CLI client for processing queries."""

import os
import subprocess
import threading
from pathlib import Path
from typing import Optional


class ClaudeClient:
    """Handles interaction with Claude CLI."""
    
    def __init__(self):
        self.current_process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self.config = None
    
    def send_query(
        self,
        text: str,
        profile_path: Optional[Path] = None,
        reset_context: bool = False
    ) -> str:
        """
        Send a query to Claude and get the response.
        
        Args:
            text: Query text
            profile_path: Optional path to profile directory
            reset_context: Whether to reset context
            
        Returns:
            Claude's response text
        """
        # Build command
        cmd = ["claude", "--print", "--output-format", "json"]  # Use JSON output for better parsing
        
        # Check for existing session
        if profile_path:
            session_file = profile_path / ".session_id"
        else:
            # Use default context directory when no profile
            session_file = Path(".context") / ".session_id"
        
        # If resetting context, delete the session file
        if reset_context and session_file and session_file.exists():
            session_file.unlink()
        
        if session_file and session_file.exists() and not reset_context:
            # Resume existing session
            session_id = session_file.read_text().strip()
            # Show full ID in verbose mode, truncated otherwise
            if hasattr(self, 'config') and self.config and self.config.verbose:
                print(f"📂 Resuming session {session_id}")
            else:
                print(f"📂 Resuming session {session_id[:8]}...")
            cmd.extend(["--resume", session_id])
        else:
            # Starting new session - Claude will generate the ID
            if hasattr(self, 'config') and self.config and self.config.verbose:
                print(f"🆕 Starting new session (Claude will assign ID)")
            else:
                print(f"🆕 Starting new session...")
            # Ensure directory exists for session file
            if session_file:
                session_file.parent.mkdir(parents=True, exist_ok=True)
        
        cmd.append(text)
        
        # Set working directory
        cwd = profile_path if profile_path else Path(".context")
        cwd.mkdir(parents=True, exist_ok=True)
        
        # In verbose mode, show the full command
        if self.config and self.config.verbose:
            print(f"🔧 Claude command: {' '.join(cmd)}")
            print(f"📁 Working directory: {cwd}")
        
        try:
            with self._lock:
                # Run Claude command
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=str(cwd),
                    env=os.environ.copy(),
                )
                
                # Get output (no timeout for conversation mode)
                stdout, stderr = self.current_process.communicate()
                
                if self.current_process.returncode != 0:
                    error_msg = stderr.strip() if stderr else "Unknown error"
                    return f"Error: {error_msg}"
                
                # Parse JSON response
                import json
                try:
                    response_data = json.loads(stdout)
                    
                    # Update session ID for next query
                    if "session_id" in response_data and session_file:
                        new_session_id = response_data["session_id"]
                        session_file.write_text(new_session_id)
                        if self.config and self.config.verbose:
                            print(f"📝 Updated session ID: {new_session_id}")
                    
                    # Extract the actual response text
                    return response_data.get("result", "").strip()
                except json.JSONDecodeError:
                    # Fallback to raw output if not JSON
                    return stdout.strip()
                
        except subprocess.TimeoutExpired:
            self.cancel()
            return "Response timed out."
        except Exception as e:
            return f"Error: {str(e)}"
        finally:
            with self._lock:
                self.current_process = None
    
    def cancel(self):
        """Cancel the current Claude process."""
        with self._lock:
            if self.current_process:
                try:
                    self.current_process.terminate()
                    self.current_process.wait(timeout=2)
                except:
                    try:
                        self.current_process.kill()
                    except:
                        pass
                finally:
                    self.current_process = None
    
    @property
    def is_processing(self) -> bool:
        """Check if currently processing a query."""
        with self._lock:
            return self.current_process is not None