"""
Cursor IDE formatter for Rules Engine.

Generates .mdc files in .cursor/rules/ directory.
"""

import yaml
from pathlib import Path
from typing import List, Dict
from .base import BaseFormatter, FormatError


class CursorFormatter(BaseFormatter):
    """Formatter for Cursor IDE .mdc files."""
    
    def __init__(self):
        super().__init__(
            name='cursor',
            description='Traditional .mdc files in .cursor/rules/ directory',
            file_extensions=['.mdc']
        )
    
    def convert(self, mdc_contents: List[str]) -> Dict[str, str]:
        """Convert .mdc contents to Cursor format (pass-through since already in .mdc format).
        
        Args:
            mdc_contents: List of .mdc file contents
            
        Returns:
            Dict mapping filename to content
        """
        self.validate_content(mdc_contents)
        
        content_map = {}
        
        for i, content in enumerate(mdc_contents):
            if not content.strip():
                continue
                
            # Extract filename from YAML front matter
            filename = self._extract_filename(content, i)
            content_map[filename] = content
        
        return content_map
    
    def save(self, content_map: Dict[str, str], target_dir: Path, repo_path: Path) -> List[str]:
        """Save .mdc files to .cursor/rules/ directory.
        
        Args:
            content_map: Dict mapping filename to content
            target_dir: Directory to save in (should be repository root)
            repo_path: Repository root path
            
        Returns:
            List of created file paths
        """
        if not content_map:
            return []
        
        # Create .cursor/rules directory
        rules_dir = target_dir / '.cursor' / 'rules'
        rules_dir.mkdir(parents=True, exist_ok=True)
        
        created_files = []
        
        for filename, content in content_map.items():
            file_path = rules_dir / filename
            
            # Ensure we don't overwrite files by adding numbers
            counter = 1
            original_path = file_path
            while file_path.exists():
                base_name = original_path.stem
                file_path = rules_dir / f'{base_name}-{counter}.mdc'
                counter += 1
            
            try:
                file_path.write_text(content, encoding='utf-8')
                created_files.append(self._safe_relative_path(file_path, repo_path))
            except (OSError, UnicodeError) as e:
                raise FormatError(f"Failed to write Cursor file {file_path}: {e}")
        
        return created_files
    
    def supports_merge(self) -> bool:
        """Cursor format supports individual files, not merging."""
        return False
    
    def _extract_filename(self, content: str, index: int) -> str:
        """Extract filename from .mdc content.
        
        Args:
            content: .mdc file content
            index: Index for fallback naming
            
        Returns:
            Filename with .mdc extension
        """
        try:
            # Parse the YAML front matter to get description
            yaml_end = content.find('---', 3)  # Find second ---
            if yaml_end > 0:
                front_matter = content[3:yaml_end].strip()
                parsed = yaml.safe_load(front_matter)
                description = parsed.get('description', f'rule-{index}')
                filename = self._slugify(description) + '.mdc'
            else:
                filename = f'rule-{index}.mdc'
        except (yaml.YAMLError, AttributeError):
            filename = f'rule-{index}.mdc'
        
        return filename
    
    def _slugify(self, text: str) -> str:
        """Convert text to a filename-safe slug.
        
        Args:
            text: Text to slugify
            
        Returns:
            Filename-safe slug
        """
        import re
        
        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = slug.strip('-')
        
        # Truncate if too long
        if len(slug) > 50:
            slug = slug[:50].rstrip('-')
        
        return slug or 'rule'