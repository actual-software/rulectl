#!/usr/bin/env python3
"""
Repository analyzer module for Rulectl.
This module handles the intelligent analysis of repositories to generate Cursor rules.
"""

import os
from pathlib import Path
from typing import Dict, List, Any, Tuple, Set, Optional, NamedTuple
import json
import re
import yaml
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass
try:
    from baml_client.async_client import b
    from baml_client.types import FileInfo, StaticAnalysisResult, RuleCandidate, StaticAnalysisRule, RuleCategory
except ImportError as e:
    import sys
    print(f"❌ Failed to import BAML client: {e}")
    print("This usually indicates a dependency version mismatch.")
    print("Try upgrading your packages:")
    print("  pip install --upgrade pydantic>=2.6.0 typing_extensions>=4.8.0 baml-py>=0.202.1")
    sys.exit(1)
import pathspec
import mimetypes
import logging
import asyncio

# Import structured logging
try:
    from .logging_config import get_logger, get_analysis_logger
except ImportError:
    try:
        from rulectl.logging_config import get_logger, get_analysis_logger
    except ImportError:
        # Fallback if logging config not available
        def get_logger(name):
            import logging
            logger = logging.getLogger(name)
            class FallbackLogger:
                def info(self, msg, **kwargs): logger.info(msg)
                def warning(self, msg, **kwargs): logger.warning(msg)
                def error(self, msg, **kwargs): logger.error(msg)
                def debug(self, msg, **kwargs): logger.debug(msg)
                def verbose(self, msg, **kwargs): logger.info(msg)  # Fallback to info for verbose
            return FallbackLogger()
        
        def get_analysis_logger():
            return get_logger("analysis")

# Import git utilities but handle import errors gracefully
try:
    from .git_utils import GitAnalyzer, GitError, get_file_importance_weights
except ImportError:
    try:
        from git_utils import GitAnalyzer, GitError, get_file_importance_weights
    except ImportError:
        GitAnalyzer = None
        GitError = Exception
        get_file_importance_weights = None

# Import rate limiter
try:
    from .rate_limiter import RateLimiter, RateLimitConfig, RateLimitStrategy
except ImportError:
    try:
        from rulectl.rate_limiter import RateLimiter, RateLimitConfig, RateLimitStrategy
    except ImportError:
        RateLimiter = None
        RateLimitConfig = None
        RateLimitStrategy = None

# Set up logging
logger = logging.getLogger(__name__)

# Maximum number of lines a file can have to be analyzed
MAX_ANALYZABLE_LINES = 2000

@dataclass
class CandidateRule:
    """Represents a candidate rule with enriched metadata."""
    slug: str
    description: str
    scope_glob: str
    bullets: List[str]
    evidence_lines: List[int]
    file: str
    edit_count: int = 0
    last_edit: Optional[datetime] = None

@dataclass
class RuleClusterMeta:
    """Metadata for a rule cluster."""
    support_files: int
    score: float
    last_touched: datetime
    total_edits: int

class RuleCluster:
    """A cluster of similar candidate rules."""
    def __init__(self, key: str):
        self.key = key
        self.rules: List[CandidateRule] = []
        self.meta: Optional[RuleClusterMeta] = None

    def add_rule(self, rule: CandidateRule):
        self.rules.append(rule)

    def calculate_meta(self):
        """Calculate metadata for this cluster."""
        if not self.rules:
            return

        support_files = len(set(rule.file for rule in self.rules))
        total_edits = sum(rule.edit_count for rule in self.rules)
        last_touched = max((rule.last_edit for rule in self.rules if rule.last_edit), default=datetime.now())

        # Score: support_files * 2 + log(1 + total_edits), capped at 10.0
        import math
        score = min(10.0, support_files * 2 + math.log1p(total_edits))

        self.meta = RuleClusterMeta(
            support_files=support_files,
            score=score,
            last_touched=last_touched,
            total_edits=total_edits
        )

class RepoAnalyzer:
    def __init__(self, repo_path: str, max_batch_size: int = 3):
        """Initialize the repository analyzer.

        Args:
            repo_path: Path to the repository
            max_batch_size: Maximum number of files to analyze in a batch
        """
        self.repo_path = Path(repo_path).resolve()  # Get absolute path
        self.max_batch_size = max_batch_size
        self.client = b
        
        # Initialize logging
        self.logger = get_logger("analyzer")
        self.analysis_logger = get_analysis_logger()
        
        # Log initialization
        self.logger.info("RepoAnalyzer initialized",
                        repo_path=str(self.repo_path),
                        max_batch_size=max_batch_size)

        # Initialize token tracker
        try:
            from .token_tracker import TokenTracker
        except ImportError:
            try:
                from rulectl.token_tracker import TokenTracker
            except ImportError:
                # Fallback if import fails
                TokenTracker = None

        self.token_tracker = TokenTracker() if TokenTracker else None

        # Initialize rate limiter
        self.rate_limiter = None
        if RateLimiter:
            try:
                config = self._load_rate_limit_config()
                self.rate_limiter = RateLimiter(config)
                logger.info(f"Rate limiter initialized with {config.requests_per_minute} requests/minute limit")
            except Exception as e:
                logger.warning(f"Failed to initialize rate limiter: {e}")
                # Fall back to default configuration
                self.rate_limiter = RateLimiter()

        self.findings = {
            "repository": {
                "structure": {},
                "patterns": [],
                "metrics": {}
            },
            "batches": [],
            "rules": []
        }

        # Track skipped files
        self.skipped_binary = set()  # Files skipped because they're binary/non-text
        self.skipped_large = set()   # Files skipped because they're too large
        self.skipped_unreadable = set()  # Files that couldn't be read
        self.skipped_config = set()  # Files skipped because they're config files

        # Check for .gitignore existence first
        self.gitignore_exists = (self.repo_path / '.gitignore').exists()

        # Load patterns
        self.ignore_spec = None
        self.default_ignore_spec = None
        self.load_gitignore()

        # Initialize mimetypes
        mimetypes.init()

    def _load_rate_limit_config(self) -> RateLimitConfig:
        """Load rate limiting configuration from config file or environment variables."""
        config = RateLimitConfig()

        # Try to load from config file
        config_path = Path(__file__).parent.parent / "config" / "rate_limiting.yaml"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    yaml_config = yaml.safe_load(f)

                # Load provider-specific settings
                if 'rate_limits' in yaml_config:
                    rate_limits = yaml_config['rate_limits']

                    # Check if we have Anthropic API key (primary provider)
                    if os.getenv("ANTHROPIC_API_KEY") and 'anthropic' in rate_limits:
                        provider_config = rate_limits['anthropic']
                        config.requests_per_minute = provider_config.get('requests_per_minute', 5)
                        config.base_delay_ms = provider_config.get('base_delay_ms', 1000)
                        config.max_delay_ms = provider_config.get('max_delay_ms', 60000)
                    elif os.getenv("OPENAI_API_KEY") and 'openai' in rate_limits:
                        provider_config = rate_limits['openai']
                        config.requests_per_minute = provider_config.get('requests_per_minute', 60)
                        config.base_delay_ms = provider_config.get('base_delay_ms', 500)
                        config.max_delay_ms = provider_config.get('max_delay_ms', 30000)
                    else:
                        # Use default settings
                        default_config = rate_limits.get('default', {})
                        config.requests_per_minute = default_config.get('requests_per_minute', 5)
                        config.base_delay_ms = default_config.get('base_delay_ms', 1000)
                        config.max_delay_ms = default_config.get('max_delay_ms', 60000)

                # Load strategy settings
                if 'strategy' in yaml_config:
                    strategy_config = yaml_config['strategy']
                    strategy_type = strategy_config.get('type', 'adaptive')
                    if strategy_type == 'constant':
                        config.strategy = RateLimitStrategy.CONSTANT
                    elif strategy_type == 'exponential':
                        config.strategy = RateLimitStrategy.EXPONENTIAL
                    else:
                        config.strategy = RateLimitStrategy.ADAPTIVE

                    config.exponential_multiplier = strategy_config.get('exponential_multiplier', 2.0)
                    config.jitter_ms = strategy_config.get('jitter_ms', 100)

                # Load batching settings
                if 'batching' in yaml_config:
                    batching_config = yaml_config['batching']
                    config.enable_batching = batching_config.get('enabled', True)
                    config.max_batch_size = batching_config.get('max_batch_size', 3)
                    config.batch_delay_ms = batching_config.get('delay_between_batches_ms', 2000)

                # Load fallback settings
                if 'fallback' in yaml_config:
                    fallback_config = yaml_config['fallback']
                    config.enable_fallback = fallback_config.get('enabled', True)
                    config.fallback_delay_ms = fallback_config.get('delay_before_fallback_ms', 5000)

            except Exception as e:
                logger.warning(f"Failed to load rate limiting config from {config_path}: {e}")

        # Override with environment variables if set
        env_requests = os.getenv("RULECTL_RATE_LIMIT_REQUESTS_PER_MINUTE")
        if env_requests:
            try:
                config.requests_per_minute = int(env_requests)
            except ValueError:
                pass

        env_delay = os.getenv("RULECTL_RATE_LIMIT_BASE_DELAY_MS")
        if env_delay:
            try:
                config.base_delay_ms = int(env_delay)
            except ValueError:
                pass

        env_strategy = os.getenv("RULECTL_RATE_LIMIT_STRATEGY")
        if env_strategy:
            if env_strategy == 'constant':
                config.strategy = RateLimitStrategy.CONSTANT
            elif env_strategy == 'exponential':
                config.strategy = RateLimitStrategy.EXPONENTIAL
            elif env_strategy == 'adaptive':
                config.strategy = RateLimitStrategy.ADAPTIVE

        env_batching = os.getenv("RULECTL_RATE_LIMIT_BATCHING_ENABLED")
        if env_batching:
            config.enable_batching = env_batching.lower() in ('true', '1', 'yes')

        return config

    def load_gitignore(self) -> None:
        """Load .gitignore patterns."""
        gitignore_path = self.repo_path / '.gitignore'

        # Load comprehensive default patterns for safety - be VERY aggressive
        default_patterns = [
            # ===== EXECUTABLE AND BINARY FILES =====
            '*.exe', '*.dll', '*.so', '*.dylib', '*.bin', '*.com', '*.bat',  # Executables
            '*.o', '*.obj', '*.a', '*.lib', '*.out', '*.app',  # Object/compiled files
            '*.pyc', '*.pyo', '*.pyd', '__pycache__/',  # Python compiled
            '*.class', '*.jar', '*.war', '*.ear',  # Java compiled
            '*.beam', '*.plt',  # Erlang/Elixir compiled
            '*.rlib', '*.rmeta',  # Rust compiled
            '*.wasm',  # WebAssembly

            # ===== ARCHIVES AND PACKAGES =====
            '*.zip', '*.tar', '*.gz', '*.bz2', '*.xz', '*.7z', '*.rar', '*.arj',
            '*.cab', '*.msi', '*.deb', '*.rpm', '*.dmg', '*.pkg', '*.snap',
            '*.tgz', '*.tbz2', '*.txz',  # Compressed archives
            '*.iso', '*.img', '*.vdi', '*.vmdk',  # Disk images

            # ===== MEDIA FILES =====
            # Images (all common formats)
            '*.png', '*.jpg', '*.jpeg', '*.gif', '*.bmp', '*.ico', '*.icns',
            '*.svg', '*.webp', '*.tiff', '*.tif', '*.psd', '*.ai', '*.eps',
            '*.raw', '*.cr2', '*.nef', '*.dng', '*.heic', '*.avif',
            # Audio
            '*.mp3', '*.wav', '*.flac', '*.aac', '*.ogg', '*.wma', '*.m4a',
            '*.opus', '*.aiff', '*.au', '*.mid', '*.midi',
            # Video
            '*.mp4', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm', '*.mkv',
            '*.m4v', '*.3gp', '*.ogv', '*.asf', '*.rm', '*.swf',

            # ===== FONTS =====
            '*.ttf', '*.otf', '*.woff', '*.woff2', '*.eot', '*.fon', '*.fnt',

            # ===== DOCUMENTS AND OFFICE FILES =====
            '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx',
            '*.odt', '*.ods', '*.odp', '*.rtf', '*.pages', '*.numbers', '*.key',
            '*.epub', '*.mobi', '*.azw', '*.azw3',

            # ===== DATABASES =====
            '*.db', '*.sqlite', '*.sqlite3', '*.mdb', '*.accdb', '*.dbf',
            '*.frm', '*.myd', '*.myi', '*.ibd',

            # ===== CERTIFICATES AND SECURITY =====
            '*.pem', '*.key', '*.cert', '*.crt', '*.cer', '*.der', '*.p12',
            '*.pfx', '*.jks', '*.keystore', '*.truststore',

            # ===== ENVIRONMENT AND SECRETS =====
            '.env', '.env.*', '.environment',  # Environment files
            '*password*', '*secret*', '*credential*', '*api*key*',  # Potential secrets
            '*.secrets', '.aws/', '.ssh/', '.gnupg/',  # Config directories

            # ===== VERSION CONTROL =====
            '.git/', '.svn/', '.hg/', '.bzr/', '.fossil-settings/',

            # ===== BUILD OUTPUT AND DEPENDENCIES =====
            # JavaScript/Node
            'node_modules/', 'bower_components/', 'jspm_packages/',
            'dist/', 'build/', 'out/', 'public/', 'static/',
            '.next/', '.nuxt/', '.vuepress/', '.svelte-kit/',
            'coverage/', '.nyc_output/',
            # Python
            '__pycache__/', '*.egg-info/', 'dist/', 'build/',
            '.eggs/', '.pytest_cache/', '.coverage', '.tox/',
            'venv/', 'env/', '.venv/', '.env/',
            # Ruby
            'vendor/', 'Gemfile.lock',
            # Go
            'vendor/', 'go.sum',
            # Rust
            'target/', 'Cargo.lock',
            # Java/Maven/Gradle
            'target/', '.gradle/', 'build/', 'gradle-wrapper.jar',
            # .NET
            'bin/', 'obj/', 'packages/', '*.user', '*.suo',
            # C/C++
            'Debug/', 'Release/', 'x64/', 'x86/', '.vs/',

            # ===== IDE AND EDITOR FILES =====
            '.idea/', '.vscode/', '.eclipse/', '.settings/',
            '*.swp', '*.swo', '*.tmp', '*~', '.#*', '#*#',
            '*.orig', '*.rej', '*.bak', '*.backup',
            '.project', '.classpath', '.factorypath',
            'Desktop.ini', 'ehthumbs.db',

            # ===== OS FILES =====
            '.DS_Store', '.DS_Store?', '._*', '.Spotlight-V100',
            '.Trashes', 'Thumbs.db', 'thumbs.db', 'ehthumbs.db',

            # ===== LOG AND TEMPORARY FILES =====
            '*.log', '*.log.*', '*.logs', 'logs/',
            '*.tmp', '*.temp', 'tmp/', 'temp/', 'cache/',
            '.cache/', '.tmp/', '.temp/',

            # ===== GENERATED/COMPILED FRONTEND ASSETS =====
            '*.min.js', '*.min.css', '*.bundle.js', '*.bundle.css',
            '*.chunk.js', '*.chunk.css', '*.map', '*.gz.js', '*.gz.css',

            # ===== TOOL-SPECIFIC =====
            '.cursor/rules.mdc', '.cursor/rules/',  # Our rules file
            '.rulectl/*', '.rulectl/',  # Our analysis files
            '.terraform/', 'terraform.tfstate', '*.tfstate',
            '.vagrant/', 'Vagrantfile.local',
            '.docker/', 'docker-compose.override.yml',

            # ===== DOCUMENTATION THAT WE SHOULD SKIP =====
            # Often these are not code patterns but just text
            '*.txt', '*.rtf', 'README*', 'CHANGELOG*', 'LICENSE*',
            'CONTRIBUTING*', 'AUTHORS*', 'CREDITS*', 'COPYING*',
            'INSTALL*', 'NEWS*', 'TODO*', 'HISTORY*',

            # ===== PACKAGE MANAGER LOCKS AND METADATA =====
            'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
            'Pipfile.lock', 'poetry.lock', 'Gemfile.lock',
            'composer.lock', 'mix.lock', 'rebar.lock',

            # ===== TEST FIXTURES AND MOCK DATA =====
            'fixtures/', 'mocks/', 'test-data/', 'mock-data/',
            '*.fixtures', '*.mocks', 'dummy.*', 'sample.*',

            # ===== CONFIGURATION THAT'S NOT CODE =====
            '.editorconfig', '.gitattributes', '.gitmodules',
            'robots.txt', 'sitemap.xml', 'favicon.ico',
            '.htaccess', '.nginx.conf', 'web.config',
        ]
        self.default_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', default_patterns)

        # Add patterns from .gitignore if it exists
        if self.gitignore_exists:
            with open(gitignore_path) as f:
                patterns = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Handle negation patterns
                        if line.startswith('!'):
                            # Skip negation patterns for now as they're complex to handle
                            continue
                        patterns.append(line)
                self.ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    def has_gitignore(self) -> bool:
        """Check if .gitignore exists in the repository."""
        return self.gitignore_exists

    def is_analyzable_text_file(self, file_path: Path) -> Tuple[bool, str, Optional[str]]:
        """Check if a file is a readable text file within size limits.

        Args:
            file_path: Path to the file to check

        Returns:
            Tuple[bool, str, Optional[str]]: (is_analyzable, reason_if_not, content_if_analyzable)
        """
        # EXTREMELY AGGRESSIVE CONFIG FILE SKIPPING - skip by default, AI can review later
        config_extensions = {
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.xml', '.plist', '.properties', '.env',
            '.gradle', '.maven', '.sbt', '.cmake', '.make', '.mk',
            '.dockerfile', '.containerfile'
        }

        if file_path.suffix.lower() in config_extensions:
            return False, "config_file", None

        # Comprehensive binary extensions - VERY aggressive skipping
        binary_extensions = {
            # ===== IMAGES =====
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.icns', '.tiff', '.tif',
            '.webp', '.svg', '.psd', '.ai', '.eps', '.raw', '.cr2', '.nef', '.dng',
            '.heic', '.avif', '.jfif', '.jp2', '.jpx', '.j2k', '.j2c',

            # ===== AUDIO =====
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
            '.aiff', '.au', '.mid', '.midi', '.ra', '.rm', '.3gp',

            # ===== VIDEO =====
            '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v',
            '.3gp', '.ogv', '.asf', '.rm', '.swf', '.f4v', '.vob', '.ts',

            # ===== DOCUMENTS =====
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.odt', '.ods', '.odp', '.rtf', '.pages', '.numbers', '.key',
            '.epub', '.mobi', '.azw', '.azw3', '.djvu', '.cbr', '.cbz',

            # ===== ARCHIVES =====
            '.zip', '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar', '.arj',
            '.cab', '.msi', '.deb', '.rpm', '.dmg', '.pkg', '.snap',
            '.tgz', '.tbz2', '.txz', '.lzma', '.ace', '.alz',

            # ===== EXECUTABLES =====
            '.exe', '.dll', '.so', '.dylib', '.app', '.deb', '.rpm', '.msi',
            '.com', '.bat', '.cmd', '.scr', '.gadget', '.application',

            # ===== COMPILED CODE =====
            '.pyc', '.pyo', '.pyd', '.class', '.jar', '.war', '.ear',
            '.beam', '.plt', '.rlib', '.rmeta', '.wasm',
            '.o', '.obj', '.a', '.lib', '.out', '.pdb', '.ilk', '.exp',

            # ===== DATABASES =====
            '.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.dbf',
            '.frm', '.myd', '.myi', '.ibd', '.fdb', '.gdb',

            # ===== FONTS =====
            '.ttf', '.otf', '.woff', '.woff2', '.eot', '.fon', '.fnt',
            '.pfb', '.pfm', '.afm', '.bdf', '.pcf', '.snf',

            # ===== BINARY DATA =====
            '.bin', '.dat', '.dump', '.img', '.iso', '.toast', '.vcd',
            '.crx', '.xpi', '.oex', '.ipa', '.apk', '.appx',

            # ===== CERTIFICATES =====
            '.pem', '.key', '.cert', '.crt', '.cer', '.der', '.p12',
            '.pfx', '.jks', '.keystore', '.truststore',

            # ===== GENERATED/MINIFIED FILES =====
            '.min.js', '.min.css', '.bundle.js', '.bundle.css',
            '.chunk.js', '.chunk.css', '.map',

            # ===== BACKUP/TEMP =====
            '.bak', '.backup', '.tmp', '.temp', '.swp', '.swo',
            '.orig', '.rej', '~',

            # ===== DOCUMENTATION WE SKIP =====
            '.txt', '.rtf',  # Plain text files - usually not code patterns
        }

        # Known text extensions that we DO want to analyze
        text_extensions = {
            # ===== SOURCE CODE =====
            '.py', '.js', '.ts', '.jsx', '.tsx', '.vue', '.svelte',  # Modern web
            '.html', '.htm', '.css', '.scss', '.sass', '.less', '.styl',  # Web styling
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',  # C/C++
            '.java', '.kt', '.scala', '.groovy',  # JVM languages
            '.rs', '.go', '.zig', '.nim', '.d',  # Systems languages
            '.rb', '.php', '.perl', '.pl', '.lua', '.r',  # Scripting
            '.swift', '.m', '.mm',  # Apple
            '.cs', '.vb', '.fs',  # .NET
            '.dart', '.elm', '.clj', '.cljs', '.ex', '.exs',  # Functional/modern
            '.ml', '.mli', '.hs', '.lhs',  # Functional

            # Config/build files skipped by default (AI can review them later)

            # ===== SHELL/SCRIPTS =====
            '.sh', '.bash', '.zsh', '.fish', '.csh', '.tcsh',
            '.ps1', '.psm1', '.psd1',  # PowerShell
            '.bat', '.cmd',  # Windows batch (though these can be binary)

            # ===== DATABASE =====
            '.sql', '.hql', '.cql',

            # ===== MARKUP =====
            '.md', '.rst', '.tex', '.adoc', '.org',  # Keep these for code docs
            '.svg',  # SVG can contain code patterns

            # ===== SPECIAL FILES =====
            '.gitignore', '.gitattributes', '.editorconfig',
            '.eslintrc', '.prettierrc', '.babelrc',
        }

        # Check extension first
        ext = file_path.suffix.lower()
        if ext in binary_extensions:
            return False, "binary", None
        if ext in text_extensions:
            # Still verify content for text extensions
            pass
        else:
            # For unknown extensions, check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                # If we have a mime type and it's not text-based, skip
                if not (mime_type.startswith('text/') or
                       mime_type in ['application/json', 'application/javascript',
                                   'application/xml', 'application/x-yaml',
                                   'application/x-typescript']):
                    return False, "binary", None

        # Try to read and validate the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    # Read first chunk to check encoding
                    content = f.read()

                    # Check line count
                    line_count = content.count('\n') + 1
                    if line_count > MAX_ANALYZABLE_LINES:
                        return False, "too_large", None

                    # Additional binary check: look for null bytes or high concentration of non-ASCII
                    if '\0' in content[:1024]:  # Check first 1KB for null bytes
                        return False, "binary", None

                    non_ascii = sum(1 for c in content[:1024] if ord(c) > 127)
                    if non_ascii > 512:  # More than 50% non-ASCII in first 1KB
                        return False, "binary", None

                    return True, "", content

                except UnicodeDecodeError:
                    # If UTF-8 fails, try with a more permissive encoding
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f2:
                            content = f2.read()

                            # Check line count
                            line_count = content.count('\n') + 1
                            if line_count > MAX_ANALYZABLE_LINES:
                                return False, "too_large", None

                            # If we can read it with latin-1 but not utf-8, it's probably binary
                            return False, "binary", None
                    except:
                        return False, "unreadable", None

        except Exception as e:
            return False, "unreadable", None

    def should_analyze_file(self, file_path: str) -> bool:
        """Check if a file should be analyzed based on .gitignore patterns."""
        # Convert to relative path if absolute
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.repo_path)
            except ValueError:
                return False

        # Convert to string for pathspec
        rel_path = str(path)

        # Always check against default patterns for safety
        if self.default_ignore_spec.match_file(rel_path):
            return False

        # Only check against .gitignore patterns if they exist
        if self.gitignore_exists and self.ignore_spec.match_file(rel_path):
            return False

        return True

    def count_analyzable_files(self) -> Tuple[int, Dict[str, int]]:
        """Count files and categorize them by status.

        Returns:
            Tuple containing:
            - Total count of files to analyze
            - Dictionary of extension counts for files to analyze
        """
        total_count = 0
        extension_counts = {}

        for root, _, files in os.walk(self.repo_path):
            rel_path = Path(root).relative_to(self.repo_path)
            for file in files:
                file_path = str(rel_path / file)
                full_path = self.repo_path / file_path

                # First check gitignore patterns
                if not self.should_analyze_file(file_path):
                    continue

                # Then check if it's a text file
                is_analyzable, reason, _ = self.is_analyzable_text_file(full_path)
                if not is_analyzable:
                    if reason == "binary":
                        self.skipped_binary.add(file_path)
                    elif reason == "too_large":
                        self.skipped_large.add(file_path)
                    elif reason == "unreadable":
                        self.skipped_unreadable.add(file_path)
                    elif reason == "config_file":
                        self.skipped_config.add(file_path)
                    continue

                # If we get here, the file is analyzable
                total_count += 1
                ext = Path(file).suffix
                if ext:  # Only count if extension exists
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1

        return total_count, extension_counts

    def analyze_structure(self) -> Dict[str, Any]:
        """Analyze the repository structure and create a map."""
        structure = {
            "file_types": {},
            "directories": {},
            "entry_points": [],
            "dependencies": {}
        }

        # Walk the repository
        for root, dirs, files in os.walk(self.repo_path):
            rel_path = Path(root).relative_to(self.repo_path)

            # Filter files based on gitignore
            filtered_files = [f for f in files if self.should_analyze_file(str(rel_path / f))]

            if filtered_files:  # Only add directory if it has files to analyze
                structure["directories"][str(rel_path)] = {
                    "files": filtered_files,
                    "subdirs": dirs
                }

                # Analyze file types
                for file in filtered_files:
                    ext = Path(file).suffix
                    structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1

        self.findings["repository"]["structure"] = structure
        return structure

    def create_batches(self) -> List[List[str]]:
        """Create smart batches of related files for analysis.

        This method creates batches that are limited both by:
        1. Number of files (max_batch_size)
        2. Total content size (to avoid API limits)
        """
        batches = []
        current_batch = []
        current_batch_size = 0
        max_batch_content = 500000  # 500KB total content per batch

        # Helper to check if adding a file would exceed limits
        def would_exceed_limits(file_path: Path, current_size: int) -> Tuple[bool, int]:
            try:
                file_size = file_path.stat().st_size
                return (current_size + file_size > max_batch_content), file_size
            except OSError:
                return True, 0

        # Group files by directory for now
        for dir_info in self.findings["repository"]["structure"]["directories"].values():
            for file in dir_info["files"]:
                file_path = self.repo_path / file

                # Check if adding this file would exceed batch limits
                would_exceed, file_size = would_exceed_limits(file_path, current_batch_size)

                # If this file would exceed limits, start a new batch
                if would_exceed or len(current_batch) >= self.max_batch_size:
                    if current_batch:  # Only add non-empty batches
                        batches.append(current_batch)
                        current_batch = []
                        current_batch_size = 0

                current_batch.append(file)
                current_batch_size += file_size

                # If this single file filled a batch, add it
                if len(current_batch) >= self.max_batch_size:
                    batches.append(current_batch)
                    current_batch = []
                    current_batch_size = 0

        # Add any remaining files
        if current_batch:
            batches.append(current_batch)

        return batches

    def get_all_analyzable_files(self) -> List[str]:
        """Get all files that should be analyzed as a flat list.

        Returns:
            List of file paths (relative to repo) that should be analyzed
        """
        analyzable_files = []

        for root, _, files in os.walk(self.repo_path):
            rel_path = Path(root).relative_to(self.repo_path)
            for file in files:
                file_path = str(rel_path / file)
                full_path = self.repo_path / file_path

                # First check gitignore patterns
                if not self.should_analyze_file(file_path):
                    continue

                # Then check if it's a text file
                is_analyzable, reason, _ = self.is_analyzable_text_file(full_path)
                if not is_analyzable:
                    if reason == "binary":
                        self.skipped_binary.add(file_path)
                    elif reason == "too_large":
                        self.skipped_large.add(file_path)
                    elif reason == "unreadable":
                        self.skipped_unreadable.add(file_path)
                    elif reason == "config_file":
                        self.skipped_config.add(file_path)
                    continue

                analyzable_files.append(file_path)

        return analyzable_files

    async def analyze_file(self, file_path: str) -> Optional[StaticAnalysisResult]:
        """Analyze a single file using LLM through BAML.

        Args:
            file_path: Path to the file to analyze (relative to repo)

        Returns:
            StaticAnalysisResult if analysis succeeds, None if file should be skipped
        """
        self.logger.debug("Starting file analysis", file_path=file_path)
        
        full_path = self.repo_path / file_path
        if not full_path.exists() or not self.should_analyze_file(str(file_path)):
            self.logger.debug("File skipped - does not exist or should not be analyzed", file_path=file_path)
            return None

        is_analyzable, reason, content = self.is_analyzable_text_file(full_path)

        if not is_analyzable:
            self.logger.debug("File not analyzable", file_path=file_path, reason=reason)
            if reason == "binary":
                self.skipped_binary.add(file_path)
            elif reason == "too_large":
                self.skipped_large.add(file_path)
            elif reason == "unreadable":
                self.skipped_unreadable.add(file_path)
            elif reason == "config_file":
                self.skipped_config.add(file_path)
            return None

        # Create FileInfo object
        file_info = FileInfo(
            path=str(file_path),
            content=content,
            extension=full_path.suffix
        )

        # Analyze individual file with rate limiting and token tracking
        baml_options = self.token_tracker.get_baml_options() if self.token_tracker else {}

        try:
            self.logger.verbose("Calling LLM for file analysis", 
                              file_path=file_path, 
                              content_length=len(content),
                              has_rate_limiter=self.rate_limiter is not None)
            
            if self.rate_limiter:
                # Use rate limiter for API calls
                analysis = await self.rate_limiter.execute_with_rate_limiting(
                    self._analyze_file_internal,
                    file_info,
                    baml_options
                )
            else:
                # Fall back to direct call if rate limiter not available
                analysis = await self._analyze_file_internal(file_info, baml_options)

        except Exception as e:
            # Handle rate limit errors specifically
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "too many requests" in error_str:
                self.logger.error("Rate limit hit during file analysis", 
                                file_path=file_path, 
                                error=str(e))
                logger.warning(f"Rate limit hit while analyzing {file_path}: {e}")

                # If we have a rate limiter, wait and retry
                if self.rate_limiter:
                    self.logger.info("Waiting for rate limit to reset", wait_seconds=60)
                    logger.info("Waiting for rate limit to reset...")
                    await asyncio.sleep(60)  # Wait 1 minute
                    try:
                        analysis = await self.rate_limiter.execute_with_rate_limiting(
                            self._analyze_file_internal,
                            file_info,
                            baml_options
                        )
                        self.logger.info("File analysis successful after retry", file_path=file_path)
                    except Exception as retry_error:
                        logger.error(f"Retry failed for {file_path}: {retry_error}")
                        return None
                else:
                    logger.error(f"Rate limit error and no rate limiter available for {file_path}")
                    return None
            else:
                # Other types of errors
                self.logger.error("File analysis failed", 
                                file_path=file_path, 
                                error=str(e),
                                error_type=type(e).__name__)
                logger.error(f"Error analyzing {file_path}: {e}")
                return None

        # Track token usage from this call
        if self.token_tracker:
            self.token_tracker.track_call_from_collector('file_analysis', 'claude-sonnet-4-20250514')

        # Store the serialized version in findings
        self.findings["batches"].append(analysis.model_dump())
        
        # Log successful completion
        self.logger.info("File analysis completed successfully",
                        file_path=file_path,
                        rules_found=len(analysis.rules) if hasattr(analysis, 'rules') else 0)

        return analysis

    async def _analyze_file_internal(self, file_info: FileInfo, baml_options: dict) -> StaticAnalysisResult:
        """Internal method to analyze a file - used by rate limiter."""
        return await self.client.AnalyzeFileForConventions(file=file_info, baml_options=baml_options)

    # Keep the batch method for backward compatibility, but mark it as deprecated
    async def analyze_batch(self, batch: List[str]) -> List[StaticAnalysisResult]:
        """Analyze a batch of files using LLM through BAML.

        DEPRECATED: Use analyze_file() for individual file analysis instead.

        Args:
            batch: List of file paths to analyze

        Returns:
            List of StaticAnalysisResult, one for each analyzed file
        """
        results = []

        for file_path in batch:
            result = await self.analyze_file(file_path)
            if result:
                results.append(result)

        return results

    async def analyze_files_with_rate_limiting(self, file_paths: List[str]) -> List[StaticAnalysisResult]:
        """Analyze multiple files with intelligent rate limiting and batching.

        This method is more efficient than analyzing files one by one as it:
        - Uses batch processing to reduce API calls
        - Applies rate limiting between batches
        - Handles rate limit errors gracefully
        - Provides progress feedback

        Args:
            file_paths: List of file paths to analyze

        Returns:
            List of StaticAnalysisResult, one for each successfully analyzed file
        """
        if not file_paths:
            return []

        results = []
        failed_files = []

        if self.rate_limiter and self.rate_limiter.config.enable_batching:
            # Use batch processing with rate limiting
            logger.info(f"Using batch processing with rate limiting (batch size: {self.rate_limiter.config.max_batch_size})")

            # Process files in batches
            batch_size = self.rate_limiter.config.max_batch_size
            for i in range(0, len(file_paths), batch_size):
                batch = file_paths[i:i + batch_size]
                logger.info(f"Processing batch {i//batch_size + 1}/{(len(file_paths) + batch_size - 1)//batch_size} ({len(batch)} files)")

                # Process this batch
                batch_results = []
                for file_path in batch:
                    try:
                        result = await self.analyze_file(file_path)
                        if result:
                            batch_results.append(result)
                        else:
                            failed_files.append((file_path, "Analysis returned None"))
                    except Exception as e:
                        logger.error(f"Failed to analyze {file_path}: {e}")
                        failed_files.append((file_path, str(e)))

                results.extend(batch_results)

                # Add delay between batches if not the last batch
                if i + batch_size < len(file_paths):
                    delay = self.rate_limiter.config.batch_delay_ms / 1000.0
                    logger.info(f"Batch completed. Waiting {delay:.2f} seconds before next batch...")
                    await asyncio.sleep(delay)
        else:
            # Fall back to individual file processing
            logger.info("Using individual file processing (batching disabled)")
            for file_path in file_paths:
                try:
                    result = await self.analyze_file(file_path)
                    if result:
                        results.append(result)
                    else:
                        failed_files.append((file_path, "Analysis returned None"))
                except Exception as e:
                    logger.error(f"Failed to analyze {file_path}: {e}")
                    failed_files.append((file_path, str(e)))

        # Log summary
        if failed_files:
            logger.warning(f"Failed to analyze {len(failed_files)} files:")
            for file_path, reason in failed_files[:5]:  # Show first 5 failures
                logger.warning(f"  - {file_path}: {reason}")
            if len(failed_files) > 5:
                logger.warning(f"  ... and {len(failed_files) - 5} more failures")

        logger.info(f"Successfully analyzed {len(results)}/{len(file_paths)} files")
        return results

    def get_file_importance_weights(self, analyzed_files: Optional[List[str]] = None) -> Dict[str, float]:
        """Get importance weights for files based on git history.

        Args:
            analyzed_files: Optional list of file paths to limit analysis to.
                          If None, analyzes all files in git history.

        Returns:
            Dictionary mapping file paths to importance scores (0.0 to 1.0)
            Empty dict if git analysis fails or is unavailable
        """
        if not GitAnalyzer or not get_file_importance_weights:
            return {}

        try:
            all_weights = get_file_importance_weights(str(self.repo_path))

            # Filter to only analyzed files if provided
            if analyzed_files is not None:
                analyzed_set = set(analyzed_files)
                filtered_weights = {
                    path: weight for path, weight in all_weights.items()
                    if path in analyzed_set
                }
                return filtered_weights

            return all_weights
        except GitError:
            # If git analysis fails, return empty weights (all files equal importance)
            return {}

    def apply_importance_weights(self, analyses: List[StaticAnalysisResult],
                               importance_weights: Dict[str, float]) -> List[Tuple[StaticAnalysisResult, float]]:
        """Apply importance weights to analysis results.

        Args:
            analyses: List of static analysis results
            importance_weights: Dictionary mapping file paths to importance scores

        Returns:
            List of tuples containing (analysis_result, importance_weight)
        """
        weighted_analyses = []

        for analysis in analyses:
            # Get importance weight for this file (default to 0.1 if not found)
            weight = importance_weights.get(analysis.file, 0.1)
            weighted_analyses.append((analysis, weight))

        return weighted_analyses

    def _slugify(self, text: str) -> str:
        """Convert text to kebab-case slug."""
        # Remove special characters and replace with hyphens
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    def _convert_to_candidate_rules(self, analyses: List[StaticAnalysisResult],
                                  git_stats: Dict[str, Dict[str, Any]]) -> List[CandidateRule]:
        """Convert StaticAnalysisResult objects to CandidateRule objects with git metadata."""
        candidate_rules = []

        for analysis in analyses:
            file_stats = git_stats.get(analysis.file, {})
            edit_count = file_stats.get('total', 0)
            last_edit = file_stats.get('last_edit')

            for rule in analysis.rules:
                candidate_rule = CandidateRule(
                    slug=rule.slug,
                    description=rule.description,
                    scope_glob=rule.scope_glob,
                    bullets=rule.bullets,
                    evidence_lines=rule.evidence_lines,
                    file=analysis.file,
                    edit_count=edit_count,
                    last_edit=last_edit
                )
                candidate_rules.append(candidate_rule)

        return candidate_rules

    def _cluster_rules(self, candidate_rules: List[CandidateRule]) -> Dict[str, RuleCluster]:
        """Cluster rules by slug/description similarity using semantic keywords."""
        clusters = {}

        # Define semantic keyword groups for clustering
        keyword_groups = {
            'pathlib-usage': ['pathlib', 'path', 'os.path', 'file-path', 'directory'],
            'git-operations': ['git', 'repository', 'branch', 'commit', 'repo'],
            'error-handling': ['error', 'exception', 'handle', 'catch', 'try-except'],
            'api-management': ['api', 'key', 'credential', 'authentication', 'token'],
            'baml-integration': ['baml', 'client', 'gpt', 'llm', 'generate'],
            'build-process': ['build', 'compile', 'executable', 'platform', 'pyinstaller'],
            'testing-patterns': ['test', 'mock', 'fixture', 'temporary', 'temp'],
            'configuration': ['config', 'setup', 'env', 'environment', 'dotenv'],
            'file-operations': ['file', 'read', 'write', 'analyze', 'text', 'binary'],
            'validation': ['validate', 'check', 'verify', 'ensure', 'confirm'],
            'data-structures': ['dataclass', 'class', 'structure', 'type', 'schema'],
            'cli-patterns': ['cli', 'command', 'entry-point', 'main', 'console'],
            'package-management': ['package', 'dependency', 'install', 'requirements', 'setup'],
            'code-style': ['naming', 'convention', 'format', 'style', 'pattern'],
        }

        def get_cluster_key(rule: CandidateRule) -> str:
            """Determine the best cluster key for a rule based on semantic similarity."""
            text = f"{rule.slug} {rule.description}".lower()

            # Check against keyword groups
            for group_name, keywords in keyword_groups.items():
                if any(keyword in text for keyword in keywords):
                    return group_name

            # Fallback: try to extract common patterns from slug
            slug_parts = rule.slug.split('-')
            if len(slug_parts) >= 2:
                # Use first two parts for clustering
                return f"{slug_parts[0]}-{slug_parts[1]}"

            # Final fallback: use the slug itself
            return rule.slug

        # Group rules by cluster key
        for rule in candidate_rules:
            cluster_key = get_cluster_key(rule)

            if cluster_key not in clusters:
                clusters[cluster_key] = RuleCluster(cluster_key)

            clusters[cluster_key].add_rule(rule)

        # Calculate metadata for each cluster
        for cluster in clusters.values():
            cluster.calculate_meta()

        return clusters

    def _choose_canonical(self, cluster: RuleCluster) -> CandidateRule:
        """Choose the canonical rule variant for a cluster."""
        if not cluster.rules:
            raise ValueError("Empty cluster")

        def avg_line(rule: CandidateRule) -> float:
            return sum(rule.evidence_lines) / len(rule.evidence_lines) if rule.evidence_lines else 0

        # Sort by: most bullets first, then lowest average line number
        sorted_rules = sorted(cluster.rules,
                            key=lambda r: (-len(r.bullets), avg_line(r)))

        canonical = sorted_rules[0]

        # If we have multiple rules in this cluster, create a merged description
        if len(cluster.rules) > 1:
            # Create a more general description for the cluster
            cluster_descriptions = {
                'pathlib-usage': 'Use pathlib for file and path operations instead of os.path',
                'git-operations': 'Follow consistent patterns for git repository operations',
                'error-handling': 'Implement proper error handling and exception management',
                'api-management': 'Manage API keys and credentials securely',
                'baml-integration': 'Use BAML client patterns for LLM integration',
                'build-process': 'Follow consistent build and compilation patterns',
                'testing-patterns': 'Use consistent testing patterns and utilities',
                'configuration': 'Handle configuration and environment variables properly',
                'file-operations': 'Follow consistent patterns for file analysis and processing',
                'validation': 'Implement proper validation and verification patterns',
                'data-structures': 'Use appropriate data structures and class definitions',
                'cli-patterns': 'Follow consistent CLI patterns and entry points',
                'package-management': 'Handle package dependencies and setup consistently',
                'code-style': 'Follow consistent naming and style conventions',
            }

            if cluster.key in cluster_descriptions:
                canonical.description = cluster_descriptions[cluster.key]
            else:
                # Fallback: use the most descriptive rule's description
                canonical.description = max(cluster.rules, key=lambda r: len(r.description)).description

        # Merge bullets from all rules in cluster, dedupe and limit to 5
        all_bullets = []
        seen_bullets = set()

        for rule in cluster.rules:
            for bullet in rule.bullets:
                # Trim to 120 chars and dedupe
                trimmed = bullet[:120].strip()
                if trimmed and trimmed not in seen_bullets:
                    all_bullets.append(trimmed)
                    seen_bullets.add(trimmed)
                    if len(all_bullets) >= 5:
                        break
            if len(all_bullets) >= 5:
                break

        # Create canonical rule with merged bullets
        canonical.bullets = all_bullets[:5]  # Ensure max 5 bullets

        # Handle scope glob - find the most common scope pattern
        glob_counts = {}
        for rule in cluster.rules:
            glob_counts[rule.scope_glob] = glob_counts.get(rule.scope_glob, 0) + 1

        # Use the most common scope glob, or create a general one
        if glob_counts:
            most_common_glob = max(glob_counts.items(), key=lambda x: x[1])[0]
            canonical.scope_glob = most_common_glob
        else:
            canonical.scope_glob = "**/*"

        # Create a better slug for merged rules
        if len(cluster.rules) > 1:
            canonical.slug = cluster.key  # Use the cluster key as the slug

        return canonical

    def _get_git_file_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get git statistics for files including edit counts and last edit dates."""
        if not GitAnalyzer:
            return {}

        try:
            analyzer = GitAnalyzer(str(self.repo_path))
            stats = analyzer.get_file_statistics()

            # Convert to format expected by candidate rules
            file_stats = {}
            for file_path, stat_dict in stats.items():
                file_stats[file_path] = {
                    'total': stat_dict.get('total', 0),
                    'last_edit': datetime.now()  # TODO: Get actual last edit date from git
                }

            return file_stats
        except GitError:
            return {}

    async def _synthesize_with_llm(self, clusters: List[RuleCluster]) -> str:
        """Use LLM to synthesize final .mdc content from rule clusters."""

        # Convert clusters to JSON format for LLM
        cluster_data = []
        for cluster in clusters:
            if not cluster.meta:
                continue

            canonical = self._choose_canonical(cluster)
            cluster_data.append({
                "slug": canonical.slug,
                "description": canonical.description,
                "scopeGlob": canonical.scope_glob,
                "bullets": canonical.bullets,
                "supportFiles": cluster.meta.support_files,
                "totalEdits": cluster.meta.total_edits
            })

        # LLM prompt for synthesis
        prompt = f"""You are "Cursor-Rule-Synthesizer", an expert at turning candidate coding-standards
into final .mdc rule files. Output **ONLY** valid Markdown (.mdc) with YAML
front-matter, no explanations.

Rules for good output:
1. Each rule becomes its own file with kebab-case filename - e.g. `tailwind-components.mdc`.
2. YAML front-matter **must** include: description, globs (array), type: autoAttached.
3. Bullets: imperative voice, ≤120 chars, ≤5 items.
4. Drop any rule whose `supportFiles` < 3 **unless** `totalEdits` ≥ 100.
5. Never mention the numbers or meta fields in the final text.
6. Keep each file ≤ 400 lines.

Return the files concatenated, separated by:
`-----8<---------- next-file ----------8<-----`

Here is the JSON array of merged candidate rules:

{json.dumps(cluster_data, indent=2)}"""

        # Use BAML client to call LLM
        # Note: This is a simplified approach - in practice you might want a dedicated BAML function
        try:
            # For now, we'll create a simple synthesis result
            # In a real implementation, you'd call the LLM with the prompt above
            return await self._create_fallback_mdc_content(clusters)
        except Exception:
            # Fallback to simple synthesis
            return await self._create_fallback_mdc_content(clusters)

    async def _create_fallback_mdc_content(self, clusters: List[RuleCluster]) -> str:
        """Create fallback .mdc content when LLM synthesis fails."""
        mdc_files = []

        for cluster in clusters:
            if not cluster.meta or cluster.meta.score < 3:
                continue

            canonical = self._choose_canonical(cluster)

            # Create YAML front matter
            front_matter = {
                'description': canonical.description,
                'globs': [canonical.scope_glob],
                'type': 'autoAttached'
            }

            yaml_content = yaml.dump(front_matter, default_flow_style=False).strip()
            bullets_content = '\n'.join(f"- {bullet}" for bullet in canonical.bullets)

            mdc_content = f"""---
{yaml_content}
---

{bullets_content}"""

            mdc_files.append(mdc_content)

        return "\n-----8<---------- next-file ----------8<-----\n".join(mdc_files)

    async def synthesize_rules_advanced(self, analyses: List[StaticAnalysisResult],
                                      importance_weights: Optional[Dict[str, float]] = None) -> Tuple[List[str], Dict[str, Any]]:
        """Advanced rule synthesis using clustering, ranking, and LLM polishing.

        Args:
            analyses: List of static analysis results
            importance_weights: Optional importance weights for files

        Returns:
            Tuple of (list of .mdc file contents, synthesis statistics)
        """
        self.logger.info("Starting advanced rule synthesis",
                        analysis_count=len(analyses),
                        has_importance_weights=importance_weights is not None)
        
        # Step 1: Get git statistics
        git_stats = self._get_git_file_stats()
        self.logger.debug("Git statistics gathered", 
                         files_with_stats=len(git_stats) if git_stats else 0)

        # Step 2: Convert to candidate rules with git metadata
        candidate_rules = self._convert_to_candidate_rules(analyses, git_stats)
        self.logger.info("Candidate rules generated", 
                        rule_count=len(candidate_rules))

        if not candidate_rules:
            self.logger.warning("No candidate rules generated - synthesis aborted")
            return [], {}

        # Step 3: Cluster rules by similarity
        clusters = self._cluster_rules(candidate_rules)

        # Log clustering details
        clustering_stats = self.log_clustering_details(candidate_rules, clusters)

        # Step 4: Filter and rank clusters by score
        # Adaptive threshold based on project maturity
        avg_commits_per_file = sum(rule.edit_count for rule in candidate_rules) / len(candidate_rules) if candidate_rules else 0
        total_unique_files = len(set(rule.file for rule in candidate_rules)) if candidate_rules else 0

        # For greenfield/new projects (low commit activity), use lower threshold
        if avg_commits_per_file <= 2 and total_unique_files <= 10:
            SCORE_THRESHOLD = 1.5  # Much lower for new projects
        elif avg_commits_per_file <= 5:
            SCORE_THRESHOLD = 2.0  # Moderate for developing projects
        else:
            SCORE_THRESHOLD = 3.0  # Original threshold for mature projects

        filtered_clusters = [
            cluster for cluster in clusters.values()
            if cluster.meta and cluster.meta.score >= SCORE_THRESHOLD
        ]

        # Sort by score (highest first)
        filtered_clusters.sort(key=lambda c: c.meta.score if c.meta else 0, reverse=True)

        # Step 5: Audit and improve merged rules using LLM
        if not filtered_clusters:
            return [], clustering_stats

        improved_rules = []
        for cluster in filtered_clusters:
            try:
                # Get the canonical (merged) rule
                canonical = self._choose_canonical(cluster)

                # Convert to StaticAnalysisRule format for auditing
                merged_rule = StaticAnalysisRule(
                    slug=canonical.slug,
                    description=canonical.description,
                    scope_glob=canonical.scope_glob,
                    bullets=canonical.bullets,
                    evidence_lines=canonical.evidence_lines
                )

                # Get original rules from this cluster
                original_rules = []
                for candidate_rule in cluster.rules:
                    original_rules.append(StaticAnalysisRule(
                        slug=candidate_rule.slug,
                        description=candidate_rule.description,
                        scope_glob=candidate_rule.scope_glob,
                        bullets=candidate_rule.bullets,
                        evidence_lines=candidate_rule.evidence_lines
                    ))

                # Only audit if we have multiple rules in the cluster
                if len(cluster.rules) > 1:
                    # Use LLM to audit and improve the merged rule
                    baml_options = self.token_tracker.get_baml_options() if self.token_tracker else {}
                    audited_rule = await self.client.AuditMergedRule(
                        cluster_key=cluster.key,
                        merged_rule=merged_rule,
                        original_rules=original_rules,
                        baml_options=baml_options
                    )

                    # Track token usage from this call
                    if self.token_tracker:
                        self.token_tracker.track_call_from_collector('rule_auditing', 'claude-sonnet-4-20250514')
                    improved_rules.append(audited_rule)
                else:
                    # Single rule clusters don't need auditing
                    improved_rules.append(merged_rule)

            except Exception as e:
                # If auditing fails, fall back to the canonical rule
                logger.warning(f"Failed to audit cluster {cluster.key}: {e}")
                canonical = self._choose_canonical(cluster)
                fallback_rule = StaticAnalysisRule(
                    slug=canonical.slug,
                    description=canonical.description,
                    scope_glob=canonical.scope_glob,
                    bullets=canonical.bullets,
                    evidence_lines=canonical.evidence_lines
                )
                improved_rules.append(fallback_rule)

        # Step 6: Convert improved rules to .mdc format
        mdc_files = []
        for rule in improved_rules:
            try:
                # Create YAML front matter
                front_matter = {
                    'description': rule.description,
                    'globs': [rule.scope_glob] if rule.scope_glob else ["**/*"],
                    'type': 'autoAttached'
                }

                yaml_content = yaml.dump(front_matter, default_flow_style=False).strip()
                bullets_content = '\n'.join(f"- {bullet}" for bullet in rule.bullets)

                mdc_content = f"""---
{yaml_content}
---

{bullets_content}"""

                mdc_files.append(mdc_content)
            except Exception as e:
                logger.warning(f"Failed to create .mdc for rule {rule.slug}: {e}")
                continue

        # Add final statistics
        clustering_stats.update({
            'filtered_clusters': len(filtered_clusters),
            'score_threshold': SCORE_THRESHOLD,
            'avg_commits_per_file': avg_commits_per_file,
            'project_maturity': 'greenfield' if SCORE_THRESHOLD == 1.5 else 'developing' if SCORE_THRESHOLD == 2.0 else 'mature',
            'final_rule_files': len(mdc_files),
            'audited_rules': len([cluster for cluster in filtered_clusters if len(cluster.rules) > 1]),
            'top_clusters': [
                {
                    'key': cluster.key,
                    'score': cluster.meta.score if cluster.meta else 0,
                    'support_files': cluster.meta.support_files if cluster.meta else 0,
                    'rule_count': len(cluster.rules)
                }
                for cluster in filtered_clusters[:10]  # Top 10 clusters
            ]
        })

        return mdc_files, clustering_stats

    # Keep the old method for backward compatibility
    async def synthesize_rules(self, analyses: List[StaticAnalysisResult],
                             importance_weights: Optional[Dict[str, float]] = None) -> List[RuleCandidate]:
        """Synthesize rules from static analysis results, optionally weighted by importance.

        Args:
            analyses: List of static analysis results
            importance_weights: Optional importance weights for files

        Returns:
            List of synthesized rule candidates
        """
        baml_options = self.token_tracker.get_baml_options() if self.token_tracker else {}

        if importance_weights:
            # Apply importance weights to analyses
            weighted_analyses = self.apply_importance_weights(analyses, importance_weights)

            # For now, we'll still pass all analyses to SynthesizeRules
            # but we could modify the BAML function to accept weights in the future
            # TODO: Update BAML schema to accept weighted analyses
            rules = await self.client.SynthesizeRules(analyses=analyses, baml_options=baml_options)
        else:
            # Generate rules without weighting
            rules = await self.client.SynthesizeRules(analyses=analyses, baml_options=baml_options)

        # Track token usage from this call
        if self.token_tracker:
            self.token_tracker.track_call_from_collector('rule_synthesis', 'claude-sonnet-4-20250514')

        # Store the serialized version in findings
        self.findings["rules"] = [rule.model_dump() for rule in rules]

        return rules

    def save_findings(self, output_path: str):
        """Save analysis findings to a JSON file."""
        with open(output_path, 'w') as f:
            json.dump(self.findings, f, indent=2)

    def save_mdc_files(self, mdc_contents: List[str], rules_dir: Path) -> List[str]:
        """Save .mdc file contents to the rules directory.

        Args:
            mdc_contents: List of .mdc file contents
            rules_dir: Path to the .cursor/rules directory

        Returns:
            List of created file paths
        """
        created_files = []

        for i, content in enumerate(mdc_contents):
            if not content.strip():
                continue

            # Extract slug from YAML front matter for filename
            try:
                # Parse the YAML front matter to get description
                yaml_end = content.find('---', 3)  # Find second ---
                if yaml_end > 0:
                    front_matter = content[3:yaml_end].strip()
                    parsed = yaml.safe_load(front_matter)
                    description = parsed.get('description', f'rule-{i}')
                    filename = self._slugify(description) + '.mdc'
                else:
                    filename = f'rule-{i}.mdc'
            except:
                filename = f'rule-{i}.mdc'

            file_path = rules_dir / filename

            # Ensure we don't overwrite files by adding numbers
            counter = 1
            while file_path.exists():
                base_name = filename.replace('.mdc', '')
                filename = f'{base_name}-{counter}.mdc'
                file_path = rules_dir / filename
                counter += 1

            # Write the file
            file_path.write_text(content, encoding='utf-8')
            created_files.append(str(file_path.relative_to(self.repo_path)))

        return created_files

    def get_git_commit_details(self) -> Dict[str, Any]:
        """Get detailed git commit statistics for logging."""
        if not GitAnalyzer:
            return {}

        try:
            analyzer = GitAnalyzer(str(self.repo_path))

            # Get file modification counts (raw commit counts)
            modification_counts = analyzer.get_file_modification_counts()

            # Get detailed file statistics
            file_stats = analyzer.get_file_statistics()

            return {
                'modification_counts': modification_counts,
                'file_stats': file_stats,
                'total_files_with_history': len(modification_counts)
            }
        except GitError:
            return {}

    def log_clustering_details(self, candidate_rules: List[CandidateRule],
                             clusters: Dict[str, RuleCluster]) -> Dict[str, Any]:
        """Log detailed information about the rule clustering process."""

        # Count raw rules per file
        rules_per_file = {}
        for rule in candidate_rules:
            if rule.file not in rules_per_file:
                rules_per_file[rule.file] = 0
            rules_per_file[rule.file] += 1

        # Analyze clusters
        cluster_stats = []
        for key, cluster in clusters.items():
            if cluster.meta:
                cluster_stats.append({
                    'key': key,
                    'rule_count': len(cluster.rules),
                    'support_files': cluster.meta.support_files,
                    'total_edits': cluster.meta.total_edits,
                    'score': cluster.meta.score,
                    'files': list(set(rule.file for rule in cluster.rules))
                })

        # Sort by score
        cluster_stats.sort(key=lambda x: x['score'], reverse=True)

        return {
            'total_raw_rules': len(candidate_rules),
            'total_clusters': len(clusters),
            'rules_per_file': rules_per_file,
            'cluster_stats': cluster_stats,
            'files_with_rules': len(rules_per_file)
        }

    def _walk_files(self):
        """Walk through all files in the repository."""
        return self.repo_path.rglob('*')

    def get_skipped_config_files(self) -> List[str]:
        """Get files that were skipped as config files but might contain useful patterns.

        Returns:
            List of config files that were skipped during analysis
        """
        return list(self.skipped_config)

    async def review_skipped_files(self, skipped_files: List[str]) -> tuple[List[str], str]:
        """Use AI to determine which skipped files should be analyzed.

        Args:
            skipped_files: List of file paths to review

        Returns:
            Tuple of (files_to_analyze, reasoning)
        """
        if not skipped_files:
            return [], "No skipped files to review"

        # Limit to reasonable number for AI review
        files_to_review = skipped_files[:20]  # Review max 20 files

        # Prepare file info for AI
        file_infos = []
        for file_path in files_to_review:
            full_path = self.repo_path / file_path
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(500)  # Truncate to first 500 chars

                file_infos.append({
                    'path': file_path,
                    'extension': full_path.suffix,
                    'content': content
                })
            except (IOError, UnicodeDecodeError):
                continue

        if not file_infos:
            return [], "No readable config files found"

        # Get project context
        project_info = f"Repository: {self.repo_path.name}"
        if hasattr(self, 'findings') and 'repository' in self.findings:
            structure = self.findings['repository']['structure']
            languages = structure.get('languages', [])
            frameworks = structure.get('frameworks', [])
            if languages:
                project_info += f", Languages: {', '.join(languages)}"
            if frameworks:
                project_info += f", Frameworks: {', '.join(frameworks)}"

        # Review with AI
        try:
            from baml_client.types import FileInfo
            baml_file_infos = [
                FileInfo(path=f['path'], content=f['content'], extension=f['extension'])
                for f in file_infos
            ]

            baml_options = self.token_tracker.get_baml_options() if self.token_tracker else {}
            result = await self.client.ReviewSkippedFiles(
                project_info=project_info,
                skipped_files=baml_file_infos,
                baml_options=baml_options
            )

            # Track token usage from this call
            if self.token_tracker:
                self.token_tracker.track_call_from_collector('file_review', 'claude-sonnet-4-20250514')

            return result.files_to_analyze, result.reasoning

        except Exception as e:
            logger.error(f"Failed to review skipped files: {e}")
            return [], f"AI review failed: {e}"