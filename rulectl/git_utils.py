#!/usr/bin/env python3
"""
Git utilities for analyzing repository history and file importance.
"""

import subprocess
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)

class GitError(Exception):
    """Custom exception for git-related errors."""
    pass

class GitAnalyzer:
    def __init__(self, repo_path: str):
        """Initialize the git analyzer.
        
        Args:
            repo_path: Path to the git repository
            
        Raises:
            GitError: If the path is not a valid git repository
        """
        self.repo_path = Path(repo_path).resolve()
        self._validate_git_repo()
        self._main_branch = self._find_main_branch()
        
    def _validate_git_repo(self) -> None:
        """Validate that the path is a git repository."""
        if not (self.repo_path / '.git').exists():
            raise GitError(f"Not a git repository: {self.repo_path}")
        
        # Test git command in the directory
        try:
            result = subprocess.run(
                ['git', 'status'],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command failed: {e.stderr}")
        except FileNotFoundError:
            raise GitError("Git is not installed or not available in PATH")
    
    def _find_main_branch(self) -> str:
        """Find the main branch name (main, master, etc.).
        
        Returns:
            Name of the main branch
            
        Raises:
            GitError: If no main branch can be determined
        """
        # Common main branch names in order of preference
        common_names = ['main', 'master', 'develop', 'dev']
        
        try:
            # Get all branches
            result = subprocess.run(
                ['git', 'branch', '-r'],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            remote_branches = [
                line.strip().replace('origin/', '') 
                for line in result.stdout.splitlines() 
                if 'origin/' in line and '->' not in line
            ]
            
            # Try to find a common main branch name
            for branch_name in common_names:
                if branch_name in remote_branches:
                    return f"origin/{branch_name}"
            
            # If no common name found, try to get the default branch
            try:
                result = subprocess.run(
                    ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                default_branch = result.stdout.strip().replace('refs/remotes/', '')
                if default_branch:
                    return default_branch
            except subprocess.CalledProcessError:
                pass
            
            # Fallback: use the first remote branch or local main/master
            if remote_branches:
                return f"origin/{remote_branches[0]}"
            
            # Last resort: check local branches
            result = subprocess.run(
                ['git', 'branch'],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            local_branches = [
                line.strip().replace('* ', '') 
                for line in result.stdout.splitlines()
            ]
            
            for branch_name in common_names:
                if branch_name in local_branches:
                    return branch_name
            
            if local_branches:
                return local_branches[0]
            
            raise GitError("No branches found in repository")
            
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to determine main branch: {e.stderr}")
    
    def get_file_modification_counts(self, branch: Optional[str] = None) -> Dict[str, int]:
        """Get the number of times each file has been modified in commit history.
        
        Args:
            branch: Branch to analyze (defaults to main branch)
            
        Returns:
            Dictionary mapping file paths to modification counts
            
        Raises:
            GitError: If git command fails
        """
        if branch is None:
            branch = self._main_branch
        
        try:
            # Use git log with --name-only to efficiently get all modified files
            # The --pretty=format:"" removes commit info, leaving only file names
            result = subprocess.run([
                'git', 'log', 
                '--name-only', 
                '--pretty=format:',
                branch,
                '--'  # Separator to ensure we're only looking at files
            ], 
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
            )
            
            # Count occurrences of each file
            file_counts = Counter()
            
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:  # Skip empty lines
                    file_counts[line] += 1
            
            return dict(file_counts)
            
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get file modification counts: {e.stderr}")
    
    def get_file_statistics(self, branch: Optional[str] = None) -> Dict[str, Dict[str, int]]:
        """Get detailed statistics for each file including adds, modifications, deletes.
        
        Args:
            branch: Branch to analyze (defaults to main branch)
            
        Returns:
            Dictionary mapping file paths to statistics (added, modified, deleted counts)
            
        Raises:
            GitError: If git command fails
        """
        if branch is None:
            branch = self._main_branch
        
        try:
            # Use git log with --name-status to get file status (A/M/D)
            result = subprocess.run([
                'git', 'log',
                '--name-status',
                '--pretty=format:',
                branch,
                '--'
            ],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
            )
            
            file_stats = defaultdict(lambda: {'added': 0, 'modified': 0, 'deleted': 0, 'total': 0})
            
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                
                # Parse git status format: "M filename" or "A filename" etc.
                parts = line.split('\t', 1)
                if len(parts) != 2:
                    continue
                
                status, filepath = parts
                
                # Handle different status codes
                if status.startswith('A'):
                    file_stats[filepath]['added'] += 1
                elif status.startswith('M'):
                    file_stats[filepath]['modified'] += 1
                elif status.startswith('D'):
                    file_stats[filepath]['deleted'] += 1
                elif status.startswith('R'):  # Renamed
                    # For renames, we get "R100 oldname newname"
                    if '\t' in filepath:
                        old_name, new_name = filepath.split('\t', 1)
                        file_stats[new_name]['modified'] += 1  # Count as modification of new name
                elif status.startswith('C'):  # Copied
                    if '\t' in filepath:
                        old_name, new_name = filepath.split('\t', 1)
                        file_stats[new_name]['added'] += 1  # Count as addition of new name
                
                # Update total for any recognized status
                if status[0] in 'AMDRCTX':
                    file_stats[filepath]['total'] += 1
            
            return dict(file_stats)
            
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get file statistics: {e.stderr}")
    
    def get_recent_activity(self, days: int = 30, branch: Optional[str] = None) -> Dict[str, int]:
        """Get file modification counts for recent activity within specified days.
        
        Args:
            days: Number of days to look back
            branch: Branch to analyze (defaults to main branch)
            
        Returns:
            Dictionary mapping file paths to modification counts in the time period
            
        Raises:
            GitError: If git command fails
        """
        if branch is None:
            branch = self._main_branch
        
        try:
            result = subprocess.run([
                'git', 'log',
                '--name-only',
                '--pretty=format:',
                f'--since={days} days ago',
                branch,
                '--'
            ],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
            )
            
            file_counts = Counter()
            
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    file_counts[line] += 1
            
            return dict(file_counts)
            
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get recent activity: {e.stderr}")
    
    def get_repository_info(self) -> Dict[str, any]:
        """Get general repository information.
        
        Returns:
            Dictionary with repository statistics
            
        Raises:
            GitError: If git command fails
        """
        try:
            # Get total commit count
            commit_result = subprocess.run([
                'git', 'rev-list', '--count', self._main_branch
            ],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
            )
            
            total_commits = int(commit_result.stdout.strip())
            
            # Get first commit date
            first_commit_result = subprocess.run([
                'git', 'log', '--reverse', '--pretty=format:%ai', '-1', self._main_branch
            ],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
            )
            
            # Get last commit date
            last_commit_result = subprocess.run([
                'git', 'log', '--pretty=format:%ai', '-1', self._main_branch
            ],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
            text=True
            )
            
            return {
                'repository_path': str(self.repo_path),
                'main_branch': self._main_branch,
                'total_commits': total_commits,
                'first_commit_date': first_commit_result.stdout.strip(),
                'last_commit_date': last_commit_result.stdout.strip()
            }
            
        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to get repository info: {e.stderr}")
        except ValueError as e:
            raise GitError(f"Failed to parse git output: {e}")

def get_file_importance_weights(repo_path: str, 
                              recent_days: int = 90,
                              recency_weight: float = 0.3) -> Dict[str, float]:
    """Get importance weights for files based on git history.
    
    This combines total modification count with recent activity to create
    a weighted importance score for each file.
    
    Args:
        repo_path: Path to the git repository
        recent_days: Number of days to consider for recent activity
        recency_weight: Weight given to recent activity (0.0 to 1.0)
        
    Returns:
        Dictionary mapping file paths to importance scores (0.0 to 1.0)
        
    Raises:
        GitError: If git operations fail
    """
    analyzer = GitAnalyzer(repo_path)
    
    # Get total modification counts
    total_counts = analyzer.get_file_modification_counts()
    
    # Get recent activity
    recent_counts = analyzer.get_recent_activity(days=recent_days)
    
    if not total_counts:
        return {}
    
    # Normalize total counts to 0-1 range
    max_total = max(total_counts.values()) if total_counts else 1
    normalized_total = {path: count / max_total for path, count in total_counts.items()}
    
    # Normalize recent counts to 0-1 range
    max_recent = max(recent_counts.values()) if recent_counts else 1
    normalized_recent = {path: recent_counts.get(path, 0) / max_recent for path in total_counts.keys()}
    
    # Combine scores: (1 - recency_weight) * total + recency_weight * recent
    importance_scores = {}
    for path in total_counts.keys():
        total_score = normalized_total[path]
        recent_score = normalized_recent[path]
        combined_score = (1 - recency_weight) * total_score + recency_weight * recent_score
        importance_scores[path] = combined_score
    
    return importance_scores 