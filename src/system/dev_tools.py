"""
Development Tools Integration Module for JARVIS.

Provides integration with:
- VS Code / Windsurf
- Git operations
- Terminal commands
- Project management
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


@dataclass
class GitStatus:
    """Git repository status."""
    branch: str
    is_clean: bool
    staged: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


@dataclass
class GitCommit:
    """A git commit."""
    hash: str
    short_hash: str
    author: str
    date: str
    message: str


@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration: float


class GitController:
    """
    Git operations controller.
    
    Features:
    - Status checks
    - Commit with auto-generated messages
    - Push/Pull operations
    - Branch management
    - Commit history
    """
    
    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize Git controller.
        
        Args:
            repo_path: Path to git repository.
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
    
    def _run_git(self, *args: str, timeout: int = 30) -> CommandResult:
        """Run a git command."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ["git"] + list(args),
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
                duration=time.time() - start_time,
            )
        
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr="Command timed out",
                return_code=-1,
                duration=timeout,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration=time.time() - start_time,
            )
    
    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        result = self._run_git("rev-parse", "--git-dir")
        return result.success
    
    def get_status(self) -> Optional[GitStatus]:
        """Get repository status."""
        if not self.is_git_repo():
            return None
        
        # Get current branch
        branch_result = self._run_git("branch", "--show-current")
        branch = branch_result.stdout if branch_result.success else "unknown"
        
        # Get status
        status_result = self._run_git("status", "--porcelain")
        
        staged = []
        modified = []
        untracked = []
        
        if status_result.success and status_result.stdout:
            for line in status_result.stdout.split("\n"):
                if len(line) >= 3:
                    status_code = line[:2]
                    file_path = line[3:]
                    
                    if status_code[0] in "MADRC":
                        staged.append(file_path)
                    if status_code[1] == "M":
                        modified.append(file_path)
                    if status_code == "??":
                        untracked.append(file_path)
        
        # Get ahead/behind
        ahead = 0
        behind = 0
        rev_result = self._run_git("rev-list", "--left-right", "--count", f"HEAD...@{{u}}")
        if rev_result.success and rev_result.stdout:
            parts = rev_result.stdout.split()
            if len(parts) == 2:
                ahead = int(parts[0])
                behind = int(parts[1])
        
        is_clean = not staged and not modified and not untracked
        
        return GitStatus(
            branch=branch,
            is_clean=is_clean,
            staged=staged,
            modified=modified,
            untracked=untracked,
            ahead=ahead,
            behind=behind,
        )
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        status = self.get_status()
        if not status:
            return "Not a git repository"
        
        lines = [f"Branch: {status.branch}"]
        
        if status.is_clean:
            lines.append("Working tree clean")
        else:
            if status.staged:
                lines.append(f"Staged: {len(status.staged)} file(s)")
            if status.modified:
                lines.append(f"Modified: {len(status.modified)} file(s)")
            if status.untracked:
                lines.append(f"Untracked: {len(status.untracked)} file(s)")
        
        if status.ahead > 0:
            lines.append(f"Ahead by {status.ahead} commit(s)")
        if status.behind > 0:
            lines.append(f"Behind by {status.behind} commit(s)")
        
        return "\n".join(lines)
    
    def add(self, *files: str) -> bool:
        """Stage files for commit."""
        if not files:
            files = (".",)
        
        result = self._run_git("add", *files)
        return result.success
    
    def commit(self, message: str) -> Tuple[bool, str]:
        """
        Create a commit.
        
        Args:
            message: Commit message.
            
        Returns:
            Tuple of (success, message/error).
        """
        result = self._run_git("commit", "-m", message)
        
        if result.success:
            return True, f"Committed: {message}"
        else:
            return False, result.stderr or "Commit failed"
    
    def generate_commit_message(self) -> str:
        """Generate a commit message based on staged changes."""
        # Get diff of staged changes
        diff_result = self._run_git("diff", "--cached", "--stat")
        
        if not diff_result.success or not diff_result.stdout:
            return "Update files"
        
        # Parse changed files
        lines = diff_result.stdout.strip().split("\n")
        if not lines:
            return "Update files"
        
        # Get file names
        files_changed = []
        for line in lines[:-1]:  # Skip summary line
            if "|" in line:
                file_name = line.split("|")[0].strip()
                files_changed.append(file_name)
        
        if len(files_changed) == 1:
            return f"Update {files_changed[0]}"
        elif len(files_changed) <= 3:
            return f"Update {', '.join(files_changed)}"
        else:
            return f"Update {len(files_changed)} files"
    
    def push(self, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
        """Push to remote."""
        args = ["push", remote]
        if branch:
            args.append(branch)
        
        result = self._run_git(*args, timeout=60)
        
        if result.success:
            return True, "Push successful"
        else:
            return False, result.stderr or "Push failed"
    
    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> Tuple[bool, str]:
        """Pull from remote."""
        args = ["pull", remote]
        if branch:
            args.append(branch)
        
        result = self._run_git(*args, timeout=60)
        
        if result.success:
            return True, result.stdout or "Pull successful"
        else:
            return False, result.stderr or "Pull failed"
    
    def get_recent_commits(self, count: int = 5) -> List[GitCommit]:
        """Get recent commits."""
        format_str = "%H|%h|%an|%ar|%s"
        result = self._run_git("log", f"-{count}", f"--format={format_str}")
        
        commits = []
        if result.success and result.stdout:
            for line in result.stdout.split("\n"):
                parts = line.split("|", 4)
                if len(parts) == 5:
                    commits.append(GitCommit(
                        hash=parts[0],
                        short_hash=parts[1],
                        author=parts[2],
                        date=parts[3],
                        message=parts[4],
                    ))
        
        return commits
    
    def get_branches(self) -> List[str]:
        """Get list of branches."""
        result = self._run_git("branch", "--list", "--format=%(refname:short)")
        
        if result.success and result.stdout:
            return result.stdout.split("\n")
        return []
    
    def checkout(self, branch: str, create: bool = False) -> Tuple[bool, str]:
        """Checkout a branch."""
        args = ["checkout"]
        if create:
            args.append("-b")
        args.append(branch)
        
        result = self._run_git(*args)
        
        if result.success:
            return True, f"Switched to branch '{branch}'"
        else:
            return False, result.stderr or "Checkout failed"
    
    def diff(self, staged: bool = False) -> str:
        """Get diff output."""
        args = ["diff"]
        if staged:
            args.append("--cached")
        
        result = self._run_git(*args)
        return result.stdout if result.success else ""


class VSCodeController:
    """
    VS Code / Windsurf integration.
    
    Features:
    - Open projects
    - Open files
    - Execute commands
    """
    
    def __init__(self, executable: str = "code"):
        """
        Initialize VS Code controller.
        
        Args:
            executable: VS Code executable name.
        """
        self.executable = executable
    
    def _run_code(self, *args: str) -> CommandResult:
        """Run a VS Code command."""
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [self.executable] + list(args),
                capture_output=True,
                text=True,
                timeout=30,
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
                duration=time.time() - start_time,
            )
        
        except FileNotFoundError:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"'{self.executable}' not found. Is VS Code installed?",
                return_code=-1,
                duration=time.time() - start_time,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration=time.time() - start_time,
            )
    
    def is_available(self) -> bool:
        """Check if VS Code is available."""
        result = self._run_code("--version")
        return result.success
    
    def open_folder(self, path: Path) -> bool:
        """Open a folder in VS Code."""
        result = self._run_code(str(path))
        return result.success
    
    def open_file(self, path: Path, line: Optional[int] = None) -> bool:
        """
        Open a file in VS Code.
        
        Args:
            path: File path.
            line: Optional line number to go to.
        """
        if line:
            result = self._run_code("--goto", f"{path}:{line}")
        else:
            result = self._run_code(str(path))
        
        return result.success
    
    def open_new_window(self, path: Optional[Path] = None) -> bool:
        """Open a new VS Code window."""
        args = ["--new-window"]
        if path:
            args.append(str(path))
        
        result = self._run_code(*args)
        return result.success
    
    def diff_files(self, file1: Path, file2: Path) -> bool:
        """Open diff view for two files."""
        result = self._run_code("--diff", str(file1), str(file2))
        return result.success
    
    def install_extension(self, extension_id: str) -> bool:
        """Install a VS Code extension."""
        result = self._run_code("--install-extension", extension_id)
        return result.success
    
    def list_extensions(self) -> List[str]:
        """List installed extensions."""
        result = self._run_code("--list-extensions")
        if result.success and result.stdout:
            return result.stdout.split("\n")
        return []


class TerminalController:
    """
    Terminal command execution.
    
    Features:
    - Safe command execution
    - Output capture
    - Timeout handling
    """
    
    # Blocked commands for safety
    BLOCKED_PATTERNS = [
        "rm -rf /", "rm -rf ~", "rm -rf *",
        "del /f /s /q", "format",
        "shutdown", "reboot", "halt",
        ":(){", "fork bomb",
        "dd if=", "> /dev/",
        "mkfs", "fdisk",
    ]
    
    def __init__(self, working_dir: Optional[Path] = None):
        """
        Initialize terminal controller.
        
        Args:
            working_dir: Default working directory.
        """
        self.working_dir = working_dir or Path.cwd()
    
    def _is_safe(self, command: str) -> bool:
        """Check if command is safe to execute."""
        cmd_lower = command.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in cmd_lower:
                return False
        return True
    
    def run(
        self,
        command: str,
        working_dir: Optional[Path] = None,
        timeout: int = 30,
        shell: bool = True,
    ) -> CommandResult:
        """
        Run a terminal command.
        
        Args:
            command: Command to run.
            working_dir: Working directory.
            timeout: Timeout in seconds.
            shell: Use shell execution.
            
        Returns:
            CommandResult with output.
        """
        if not self._is_safe(command):
            return CommandResult(
                success=False,
                stdout="",
                stderr="Command blocked for safety reasons",
                return_code=-1,
                duration=0,
            )
        
        start_time = time.time()
        cwd = str(working_dir or self.working_dir)
        
        try:
            result = subprocess.run(
                command,
                shell=shell,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return CommandResult(
                success=result.returncode == 0,
                stdout=result.stdout.strip(),
                stderr=result.stderr.strip(),
                return_code=result.returncode,
                duration=time.time() - start_time,
            )
        
        except subprocess.TimeoutExpired:
            return CommandResult(
                success=False,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1,
                duration=timeout,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                stdout="",
                stderr=str(e),
                return_code=-1,
                duration=time.time() - start_time,
            )
    
    def run_python(self, script: str, timeout: int = 60) -> CommandResult:
        """Run a Python script."""
        return self.run(f"python -c \"{script}\"", timeout=timeout)
    
    def run_pip(self, *args: str) -> CommandResult:
        """Run a pip command."""
        return self.run(f"pip {' '.join(args)}")


class DevToolsManager:
    """
    High-level development tools manager.
    
    Provides unified interface for all dev tools.
    """
    
    def __init__(
        self,
        repo_path: Optional[Path] = None,
        vscode_executable: str = "code",
    ):
        """
        Initialize dev tools manager.
        
        Args:
            repo_path: Git repository path.
            vscode_executable: VS Code executable.
        """
        self.git = GitController(repo_path)
        self.vscode = VSCodeController(vscode_executable)
        self.terminal = TerminalController(repo_path)
    
    def get_project_status(self) -> Dict[str, Any]:
        """Get overall project status."""
        git_status = self.git.get_status()
        
        return {
            "git": {
                "is_repo": git_status is not None,
                "branch": git_status.branch if git_status else None,
                "is_clean": git_status.is_clean if git_status else None,
                "changes": {
                    "staged": len(git_status.staged) if git_status else 0,
                    "modified": len(git_status.modified) if git_status else 0,
                    "untracked": len(git_status.untracked) if git_status else 0,
                } if git_status else {},
            },
            "vscode_available": self.vscode.is_available(),
        }
    
    def quick_commit(self, message: Optional[str] = None) -> Tuple[bool, str]:
        """
        Quick commit all changes.
        
        Args:
            message: Commit message (auto-generated if not provided).
            
        Returns:
            Tuple of (success, message).
        """
        # Stage all changes
        if not self.git.add("."):
            return False, "Failed to stage changes"
        
        # Generate message if not provided
        if not message:
            message = self.git.generate_commit_message()
        
        # Commit
        return self.git.commit(message)
    
    def sync_repo(self) -> Tuple[bool, str]:
        """
        Sync repository (pull then push).
        
        Returns:
            Tuple of (success, message).
        """
        # Pull first
        success, msg = self.git.pull()
        if not success:
            return False, f"Pull failed: {msg}"
        
        # Push
        success, msg = self.git.push()
        if not success:
            return False, f"Push failed: {msg}"
        
        return True, "Repository synced successfully"
