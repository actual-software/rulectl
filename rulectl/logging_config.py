#!/usr/bin/env python3
"""
Centralized logging configuration for Rulectl.
Provides structured logging with multiple handlers for different log types.
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import os

# Add custom VERBOSE log level
VERBOSE = 15  # Between INFO (20) and DEBUG (10)
logging.addLevelName(VERBOSE, "VERBOSE")

def verbose(self, message, *args, **kwargs):
    """Log with VERBOSE level."""
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kwargs)

# Add verbose method to Logger class
logging.Logger.verbose = verbose


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)


class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str, base_logger: logging.Logger):
        self.name = name
        self.logger = base_logger
        
    def debug(self, message: str, **kwargs):
        """Log debug message with optional structured data."""
        self._log(logging.DEBUG, message, kwargs)
        
    def verbose(self, message: str, **kwargs):
        """Log verbose message with optional structured data."""
        self._log(VERBOSE, message, kwargs)
        
    def info(self, message: str, **kwargs):
        """Log info message with optional structured data."""
        self._log(logging.INFO, message, kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message with optional structured data."""
        self._log(logging.WARNING, message, kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message with optional structured data."""
        self._log(logging.ERROR, message, kwargs)
        
    def critical(self, message: str, **kwargs):
        """Log critical message with optional structured data."""
        self._log(logging.CRITICAL, message, kwargs)
        
    def _log(self, level: int, message: str, extra_fields: Dict[str, Any]):
        """Internal method to log with extra fields."""
        if extra_fields:
            # Create a custom LogRecord with extra fields
            record = self.logger.makeRecord(
                self.logger.name, level, "", 0, message, (), None
            )
            record.extra_fields = extra_fields
            self.logger.handle(record)
        else:
            self.logger.log(level, message)


class LoggingConfig:
    """Centralized logging configuration for Rulectl."""
    
    def __init__(self, log_dir: Optional[Path] = None, log_level: str = "INFO"):
        self.log_dir = log_dir or (Path.home() / ".rulectl" / "logs")
        
        # Handle custom VERBOSE level
        if log_level.upper() == "VERBOSE":
            self.log_level = VERBOSE
        else:
            self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        
        self.loggers = {}
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set up root logger
        self._setup_root_logger()
        
    def _setup_root_logger(self):
        """Configure the root logger with appropriate handlers."""
        root_logger = logging.getLogger("rulectl")
        root_logger.setLevel(self.log_level)
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Console handler for user-facing output
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Main log file handler (rotating)
        main_log_file = self.log_dir / "rulectl.log"
        main_handler = logging.handlers.RotatingFileHandler(
            main_log_file, maxBytes=10*1024*1024, backupCount=5
        )
        main_handler.setLevel(self.log_level)
        main_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        root_logger.addHandler(main_handler)
        
        # Debug log file handler (JSON format for structured data)
        debug_log_file = self.log_dir / "debug.log"
        debug_handler = logging.handlers.RotatingFileHandler(
            debug_log_file, maxBytes=50*1024*1024, backupCount=3
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(debug_handler)
        
        # API calls log (separate file for API tracking)
        api_log_file = self.log_dir / f"api-calls-{datetime.now().strftime('%Y-%m')}.log"
        api_handler = logging.handlers.RotatingFileHandler(
            api_log_file, maxBytes=20*1024*1024, backupCount=10
        )
        api_handler.setLevel(logging.DEBUG)
        api_handler.setFormatter(JSONFormatter())
        
        # Create API-specific logger
        api_logger = logging.getLogger("rulectl.api")
        api_logger.addHandler(api_handler)
        api_logger.setLevel(logging.DEBUG)
        api_logger.propagate = False  # Don't propagate to root logger
        
        # Analysis log (separate file for analysis runs)
        analysis_log_file = self.log_dir / f"analysis-{datetime.now().strftime('%Y-%m-%d')}.log"
        analysis_handler = logging.FileHandler(analysis_log_file)
        analysis_handler.setLevel(logging.INFO)
        analysis_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        analysis_handler.setFormatter(analysis_formatter)
        
        # Create analysis-specific logger
        analysis_logger = logging.getLogger("rulectl.analysis")
        analysis_logger.addHandler(analysis_handler)
        analysis_logger.setLevel(logging.INFO)
        analysis_logger.propagate = True  # Also log to main log
        
    def get_logger(self, name: str) -> StructuredLogger:
        """Get a structured logger for the given name."""
        if name not in self.loggers:
            base_logger = logging.getLogger(f"rulectl.{name}")
            self.loggers[name] = StructuredLogger(name, base_logger)
        return self.loggers[name]
        
    def get_api_logger(self) -> StructuredLogger:
        """Get the API-specific logger."""
        return StructuredLogger("api", logging.getLogger("rulectl.api"))
        
    def get_analysis_logger(self) -> StructuredLogger:
        """Get the analysis-specific logger."""
        return StructuredLogger("analysis", logging.getLogger("rulectl.analysis"))
        
    def set_console_level(self, level: str):
        """Adjust console logging level (useful for verbose mode)."""
        console_level = getattr(logging, level.upper(), logging.WARNING)
        root_logger = logging.getLogger("rulectl")
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
                handler.setLevel(console_level)
                break
                
    def get_log_directory(self) -> Path:
        """Get the current log directory."""
        return self.log_dir
        
    def cleanup_old_logs(self, days: int = 30):
        """Clean up log files older than specified days."""
        import time
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for log_file in self.log_dir.glob("*.log*"):
            try:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    logging.getLogger("rulectl").info(f"Cleaned up old log file: {log_file}")
            except Exception as e:
                logging.getLogger("rulectl").warning(f"Failed to clean up log file {log_file}: {e}")


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def setup_logging(log_dir: Optional[Path] = None, log_level: str = "INFO", 
                 verbose_console: bool = False) -> LoggingConfig:
    """Initialize logging configuration."""
    global _logging_config
    _logging_config = LoggingConfig(log_dir, log_level)
    
    if verbose_console:
        _logging_config.set_console_level("INFO")
        
    return _logging_config


def get_logger(name: str) -> StructuredLogger:
    """Get a logger instance. Auto-initializes if not already set up."""
    if _logging_config is None:
        setup_logging()
    return _logging_config.get_logger(name)


def get_api_logger() -> StructuredLogger:
    """Get the API logger instance."""
    if _logging_config is None:
        setup_logging()
    return _logging_config.get_api_logger()


def get_analysis_logger() -> StructuredLogger:
    """Get the analysis logger instance."""
    if _logging_config is None:
        setup_logging()
    return _logging_config.get_analysis_logger()


def get_log_directory() -> Path:
    """Get the current log directory."""
    if _logging_config is None:
        setup_logging()
    return _logging_config.get_log_directory()