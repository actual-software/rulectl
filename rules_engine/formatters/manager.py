"""
Format manager for Rules Engine output formatters.

Provides registry and discovery of available formatters.
"""

from typing import Dict, List, Set, Optional
from pathlib import Path
from .base import BaseFormatter, FormatError
from .cursor import CursorFormatter  
from .claude import ClaudeFormatter


class FormatManager:
    """Manages and dispatches to different output formatters."""
    
    def __init__(self):
        """Initialize the format manager with built-in formatters."""
        self.formatters: Dict[str, BaseFormatter] = {}
        self._register_builtin_formatters()
    
    def _register_builtin_formatters(self) -> None:
        """Register the built-in formatters."""
        self.register_formatter(CursorFormatter())
        self.register_formatter(ClaudeFormatter())
    
    def register_formatter(self, formatter: BaseFormatter) -> None:
        """Register a new formatter.
        
        Args:
            formatter: Formatter instance to register
            
        Raises:
            FormatError: If formatter name conflicts with existing formatter
        """
        if formatter.name in self.formatters:
            raise FormatError(f"Formatter '{formatter.name}' is already registered")
        
        self.formatters[formatter.name] = formatter
    
    def get_formatter(self, name: str) -> BaseFormatter:
        """Get a formatter by name.
        
        Args:
            name: Formatter name
            
        Returns:
            Formatter instance
            
        Raises:
            FormatError: If formatter not found
        """
        if name not in self.formatters:
            available = ', '.join(self.get_available_formats())
            raise FormatError(f"Formatter '{name}' not found. Available: {available}")
        
        return self.formatters[name]
    
    def get_available_formats(self) -> List[str]:
        """Get list of available format names.
        
        Returns:
            List of format names sorted alphabetically
        """
        return sorted(self.formatters.keys())
    
    def get_format_info(self, name: Optional[str] = None) -> Dict:
        """Get information about formatters.
        
        Args:
            name: Specific formatter name, or None for all formatters
            
        Returns:
            Dict with formatter information
        """
        if name:
            return self.get_formatter(name).get_info()
        
        return {
            fmt_name: formatter.get_info() 
            for fmt_name, formatter in self.formatters.items()
        }
    
    def convert_and_save(self, mdc_contents: List[str], formats: List[str], 
                        target_dir: Path, repo_path: Path) -> Dict[str, List[str]]:
        """Convert and save rules in specified formats.
        
        Args:
            mdc_contents: List of .mdc file contents
            formats: List of format names to generate
            target_dir: Directory to save files in
            repo_path: Repository root path
            
        Returns:
            Dict mapping format name to list of created files
            
        Raises:
            FormatError: If any format operation fails
        """
        if not mdc_contents:
            raise FormatError("No content provided for conversion")
        
        if not formats:
            raise FormatError("No formats specified")
        
        results = {}
        errors = []
        
        for format_name in formats:
            try:
                formatter = self.get_formatter(format_name)
                
                # Convert content
                content_map = formatter.convert(mdc_contents)
                
                # Save files
                created_files = formatter.save(content_map, target_dir, repo_path)
                results[format_name] = created_files
                
            except Exception as e:
                error_msg = f"Failed to process {format_name} format: {e}"
                errors.append(error_msg)
                results[format_name] = []
        
        if errors and not any(results.values()):
            # All formats failed
            raise FormatError(f"All format operations failed: {'; '.join(errors)}")
        elif errors:
            # Some formats failed, log warnings
            print(f"Warning: Some format operations failed: {'; '.join(errors)}")
        
        return results
    
    def validate_formats(self, format_names: List[str]) -> None:
        """Validate that all format names are available.
        
        Args:
            format_names: List of format names to validate
            
        Raises:
            FormatError: If any format name is invalid
        """
        available = set(self.get_available_formats())
        invalid = set(format_names) - available
        
        if invalid:
            invalid_list = ', '.join(sorted(invalid))
            available_list = ', '.join(sorted(available))
            raise FormatError(f"Invalid formats: {invalid_list}. Available: {available_list}")
    
    def resolve_format_list(self, format_spec: str) -> List[str]:
        """Resolve format specification to list of format names.
        
        Args:
            format_spec: Format specification ('cursor', 'claude', 'all', or comma-separated)
            
        Returns:
            List of format names to process
            
        Raises:
            FormatError: If format specification is invalid
        """
        if format_spec == 'all':
            # All available formats
            return self.get_available_formats()
        else:
            # Single format or comma-separated list
            formats = [f.strip() for f in format_spec.split(',') if f.strip()]
            self.validate_formats(formats)
            return formats
    
    def supports_plugin_discovery(self) -> bool:
        """Check if plugin discovery is supported.
        
        Returns:
            True if plugin discovery is available
        """
        try:
            import pkg_resources
            return True
        except ImportError:
            return False
    
    def discover_plugins(self) -> int:
        """Discover and load formatter plugins.
        
        Returns:
            Number of plugins loaded
            
        Raises:
            FormatError: If plugin discovery fails
        """
        if not self.supports_plugin_discovery():
            raise FormatError("Plugin discovery requires pkg_resources")
        
        import pkg_resources
        
        loaded_count = 0
        for entry_point in pkg_resources.iter_entry_points('rules_engine.formatters'):
            try:
                formatter_class = entry_point.load()
                formatter = formatter_class()
                
                if not isinstance(formatter, BaseFormatter):
                    print(f"Warning: Plugin '{entry_point.name}' does not inherit from BaseFormatter")
                    continue
                
                self.register_formatter(formatter)
                loaded_count += 1
                print(f"Loaded formatter plugin: {entry_point.name}")
                
            except Exception as e:
                print(f"Warning: Failed to load formatter plugin '{entry_point.name}': {e}")
        
        return loaded_count


# Global format manager instance
format_manager = FormatManager()