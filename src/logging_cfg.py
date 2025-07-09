#!/usr/bin/env python3
"""
Logging configuration module for truSDX-AI driver.
Provides centralized logging functionality with JSON formatting,
rotating files, and optional syslog integration.
"""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Custom log level for RECONNECT events
RECONNECT_LEVEL = 25
logging.addLevelName(RECONNECT_LEVEL, 'RECONNECT')

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'process': record.process,
            'thread': record.thread
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

class ColoredConsoleFormatter(logging.Formatter):
    """Console formatter with color support."""
    
    COLORS = {
        'DEBUG': '\033[1;36m',      # Cyan
        'INFO': '\033[1;32m',       # Green
        'WARNING': '\033[1;33m',    # Yellow
        'RECONNECT': '\033[1;35m',  # Magenta
        'ERROR': '\033[1;31m',      # Red
        'CRITICAL': '\033[1;37;41m' # White on red
    }
    RESET = '\033[0m'
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        reset = self.RESET if color else ''
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Create formatted message
        formatted_msg = f"{color}[{timestamp}] {record.levelname}: {record.getMessage()}{reset}"
        
        # Add exception info if present
        if record.exc_info:
            formatted_msg += '\n' + self.formatException(record.exc_info)
        
        return formatted_msg

class TrusdxLogger:
    """Enhanced logger for truSDX-AI driver."""
    
    def __init__(self):
        self.logger = logging.getLogger('trusdx')
        self.logger.setLevel(logging.DEBUG)
        self._configured = False
        self._syslog_handler = None
    
    def configure(self, verbose: bool = False, log_file: Optional[str] = None, 
                 enable_syslog: bool = False):
        """Configure the logging system.
        
        Args:
            verbose: Enable verbose (DEBUG) logging to console
            log_file: Optional custom log file path
            enable_syslog: Enable syslog handler for systemd integration
        """
        if self._configured:
            return
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler with color formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredConsoleFormatter())
        
        # Set console log level based on verbose flag
        if verbose:
            console_handler.setLevel(logging.DEBUG)
        else:
            console_handler.setLevel(logging.INFO)
        
        self.logger.addHandler(console_handler)
        
        # File handler with JSON formatting and rotation
        if log_file:
            file_path = Path(log_file)
        else:
            # Default log directory
            log_dir = Path.home() / '.cache' / 'trusdx' / 'logs'
            log_dir.mkdir(parents=True, exist_ok=True)
            file_path = log_dir / 'trusdx.log'
        
        # Rotating file handler (10MB max, keep 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            file_path, maxBytes=10*1024*1024, backupCount=5
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        
        # Optional syslog handler for systemd integration
        if enable_syslog:
            try:
                syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
                syslog_formatter = logging.Formatter(
                    'trusdx[%(process)d]: %(levelname)s - %(message)s'
                )
                syslog_handler.setFormatter(syslog_formatter)
                syslog_handler.setLevel(logging.INFO)
                self.logger.addHandler(syslog_handler)
                self._syslog_handler = syslog_handler
            except Exception as e:
                self.logger.warning(f"Failed to initialize syslog handler: {e}")
        
        self._configured = True
        self.logger.info("Logging system initialized", extra={
            'verbose': verbose,
            'log_file': str(file_path),
            'syslog_enabled': enable_syslog
        })
    
    def debug(self, msg: str, **kwargs):
        """Log debug message."""
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        """Log info message."""
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs):
        """Log warning message."""
        self.logger.warning(msg, extra=kwargs)
    
    def reconnect(self, msg: str, **kwargs):
        """Log reconnection event."""
        self.logger.log(RECONNECT_LEVEL, msg, extra=kwargs)
    
    def error(self, msg: str, **kwargs):
        """Log error message."""
        self.logger.error(msg, extra=kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Log critical message."""
        self.logger.critical(msg, extra=kwargs)
    
    def exception(self, msg: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(msg, extra=kwargs)

# Global logger instance
_trusdx_logger = TrusdxLogger()

def configure_logging(verbose: bool = False, log_file: Optional[str] = None, 
                     enable_syslog: bool = False):
    """Configure global logging settings.
    
    Args:
        verbose: Enable verbose (DEBUG) logging to console
        log_file: Optional custom log file path
        enable_syslog: Enable syslog handler for systemd integration
    """
    _trusdx_logger.configure(verbose, log_file, enable_syslog)

# Backward compatibility functions
def log(msg: str, level: str = "INFO"):
    """Backward compatibility log function.
    
    Args:
        msg: Message to log
        level: Log level (DEBUG, INFO, WARNING, RECONNECT, ERROR, CRITICAL)
    """
    level = level.upper()
    
    if level == "DEBUG":
        _trusdx_logger.debug(msg)
    elif level == "INFO":
        _trusdx_logger.info(msg)
    elif level == "WARNING":
        _trusdx_logger.warning(msg)
    elif level == "RECONNECT":
        _trusdx_logger.reconnect(msg)
    elif level == "ERROR":
        _trusdx_logger.error(msg)
    elif level == "CRITICAL":
        _trusdx_logger.critical(msg)
    elif level == "EVENT":  # Map old EVENT to INFO
        _trusdx_logger.info(msg)
    else:
        _trusdx_logger.info(msg)

# Expose logger methods for direct use
debug = _trusdx_logger.debug
info = _trusdx_logger.info
warning = _trusdx_logger.warning
reconnect = _trusdx_logger.reconnect
error = _trusdx_logger.error
critical = _trusdx_logger.critical
exception = _trusdx_logger.exception

# Legacy constants for backward compatibility
class LogLevel:
    """Log level constants (deprecated - use logging levels directly)."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    RECONNECT = "RECONNECT"
    CRITICAL = "CRITICAL"
    EVENT = "EVENT"  # Maps to INFO
