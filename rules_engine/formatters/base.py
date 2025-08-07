"""
Base formatter interface for Rules Engine output formats.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional


class FormatError(Exception):
    """Exception raised when format operations fail."""
    pass


class BaseFormatter(ABC):
    """Base class for all output formatters."""
    
    def __init__(self, name: str, description: str, file_extensions: List[str]):
        """Initialize the formatter.
        
        Args:
            name: Short name for the format (e.g., 'cursor', 'claude')
            description: Human-readable description
            file_extensions: List of file extensions this format uses (e.g., ['.mdc'])
        """
        self.name = name
        self.description = description
        self.file_extensions = file_extensions
    
    @abstractmethod
    def convert(self, mdc_contents: List[str]) -> Dict[str, str]:
        """Convert .mdc contents to this format.
        
        Args:
            mdc_contents: List of .mdc file contents
            
        Returns:
            Dict mapping filename to content
            
        Raises:
            FormatError: If conversion fails
        """
        pass
    
    @abstractmethod
    def save(self, content_map: Dict[str, str], target_dir: Path, repo_path: Path) -> List[str]:
        """Save converted content to target directory.
        
        Args:
            content_map: Dict from convert() mapping filename to content
            target_dir: Directory to save files in
            repo_path: Repository root path for relative path calculation
            
        Returns:
            List of created file paths (relative to repo_path when possible)
            
        Raises:
            FormatError: If saving fails
        """
        pass
    
    def validate_content(self, mdc_contents: List[str]) -> None:
        """Validate that content can be converted to this format.
        
        Args:
            mdc_contents: List of .mdc file contents
            
        Raises:
            FormatError: If content is invalid for this format
        """
        if not mdc_contents:
            raise FormatError(f"No content provided for {self.name} format")
        
        for i, content in enumerate(mdc_contents):
            if not content.strip():
                raise FormatError(f"Empty content at index {i} for {self.name} format")
    
    def get_info(self) -> Dict[str, Any]:
        """Get formatter information.
        
        Returns:
            Dict with formatter metadata
        """
        return {
            'name': self.name,
            'description': self.description,
            'file_extensions': self.file_extensions
        }
    
    def supports_merge(self) -> bool:
        """Whether this formatter supports merging multiple rules into single files.
        
        Returns:
            True if formatter can merge rules, False otherwise
        """
        return False
    
    def _safe_relative_path(self, file_path: Path, repo_path: Path) -> str:
        """Safely get relative path, fallback to absolute on error.
        
        Args:
            file_path: File path to make relative
            repo_path: Repository root path
            
        Returns:
            Relative path string, or absolute path if relative fails
        """
        try:
            return str(file_path.relative_to(repo_path))
        except (ValueError, OSError):
            # Handle symlinks, temp paths, cross-platform issues
            return str(file_path)