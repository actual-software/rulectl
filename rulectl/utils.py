"""
Utility functions for Rulectl.
"""

from pathlib import Path
import yaml


def validate_repository(path: str) -> bool:
    """Validate if the given path is a valid repository.
    
    Args:
        path: Path to check
        
    Returns:
        True if valid repository, False otherwise
    """
    repo_path = Path(path).resolve()
    
    # Check if path exists and is a directory
    if not repo_path.exists() or not repo_path.is_dir():
        return False
    
    # For now, we only check for .git directory
    if (repo_path / ".git").exists():
        return True
    
    return False


def check_baml_client(path: str) -> bool:
    """Check if the baml_client is available.
    
    For bundled executables, we check if baml_client can be imported.
    For development, we check if the baml_client folder exists.
    
    Args:
        path: Path to check (used in development mode)
        
    Returns:
        True if baml_client is available, False otherwise
    """
    import sys
    
    # For bundled executables, check if baml_client can be imported
    if getattr(sys, 'frozen', False):  # PyInstaller bundle
        try:
            import baml_client
            return True
        except ImportError:
            return False
    
    # For development mode, check if baml_client folder exists in the repo
    repo_path = Path(path).resolve()
    return (repo_path / "baml_client").exists() and (repo_path / "baml_client").is_dir()


def find_cursor_rules(repository_path: str) -> bool:
    """Check if cursor rules exist in the repository.
    
    Args:
        repository_path: Path to the repository
        
    Returns:
        True if rules exist, False otherwise
    """
    repo_path = Path(repository_path).resolve()
    rules_dir = repo_path / ".cursor" / "rules"
    
    # Check if the rules directory exists and contains at least one .mdc file
    if rules_dir.exists() and rules_dir.is_dir():
        return any(f.suffix == '.mdc' for f in rules_dir.glob('**/*.mdc'))
    
    return False


def analyze_project_structure(repository_path: str) -> dict[str, list[str]]:
    """Analyze the project structure to detect languages and frameworks.
    
    Args:
        repository_path: Path to the repository
        
    Returns:
        Analysis results dictionary
    """
    repo_path = Path(repository_path).resolve()
    analysis = {
        "languages": [],
        "frameworks": [],
        "build_tools": [],
        "config_files": [],
        "directory_structure": {}
    }
    
    # Language detection based on file extensions
    language_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".jsx": "React/JSX",
        ".tsx": "React/TSX",
        ".java": "Java",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".go": "Go",
        ".rs": "Rust",
        ".php": "PHP",
        ".rb": "Ruby",
        ".swift": "Swift",
        ".kt": "Kotlin"
    }
    
    # Framework detection based on files/patterns
    framework_indicators = {
        "React": ["package.json", "src/App.jsx", "src/App.tsx", "public/index.html"],
        "Vue": ["vue.config.js", "src/App.vue"],
        "Angular": ["angular.json", "src/app/app.component.ts"],
        "Django": ["manage.py", "settings.py", "urls.py"],
        "Flask": ["app.py", "wsgi.py"],
        "FastAPI": ["main.py", "requirements.txt"],
        "Express": ["package.json", "server.js", "app.js"],
        "Spring": ["pom.xml", "src/main/java"],
        "Laravel": ["composer.json", "artisan"]
    }
    
    # Build tool detection
    build_tools_map = {
        "package.json": "npm/yarn",
        "requirements.txt": "pip",
        "Pipfile": "pipenv",
        "poetry.lock": "poetry",
        "Cargo.toml": "cargo",
        "go.mod": "go modules",
        "pom.xml": "maven",
        "build.gradle": "gradle",
        "Makefile": "make"
    }
    
    file_counts = {}
    
    # Analyze files (with reasonable limits to avoid performance issues)
    file_count = 0
    max_files = 1000  # Limit analysis to avoid performance issues
    
    for file_path in repo_path.rglob("*"):
        if file_count >= max_files:
            break
            
        if file_path.is_file():
            file_count += 1
            suffix = file_path.suffix.lower()
            
            # Count language files
            if suffix in language_map:
                lang = language_map[suffix]
                file_counts[lang] = file_counts.get(lang, 0) + 1
            
            # Check for build tools
            filename = file_path.name
            if filename in build_tools_map:
                tool = build_tools_map[filename]
                if tool not in analysis["build_tools"]:
                    analysis["build_tools"].append(tool)
    
    # Determine primary languages (more than 5 files)
    analysis["languages"] = [lang for lang, count in file_counts.items() if count > 5]
    
    # Detect frameworks
    for framework, indicators in framework_indicators.items():
        for indicator in indicators:
            if (repo_path / indicator).exists():
                analysis["frameworks"].append(framework)
                break
    
    return analysis


def is_text_file(file_path: Path) -> bool:
    """Check if a file is likely a text file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if likely a text file, False otherwise
    """
    # Check by extension first
    text_extensions = {
        ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".scss",
        ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".php", ".rb", ".swift",
        ".kt", ".yaml", ".yml", ".json", ".xml", ".toml", ".ini", ".cfg", ".conf"
    }
    
    if file_path.suffix.lower() in text_extensions:
        return True
    
    # Check file content for binary data
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            
        # Simple heuristic: if chunk contains null bytes, it's likely binary
        if b"\x00" in chunk:
            return False
            
        # Try to decode as UTF-8
        try:
            chunk.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
            
    except Exception:
        return False


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"