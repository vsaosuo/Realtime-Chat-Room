
from datetime import datetime
from enum import Enum

class LogLevel(Enum):
    """Log level enumeration."""
    NONE = 0
    INFO = 1
    DEBUG = 2


class Logger:
    """Simple logger class for the server."""
    def __init__(self, level='DEBUG'):
        self._set_level(level)
    
    def _set_level(self, level):
        """Set the logging level."""
        if isinstance(level, LogLevel):
            self.level = level
        elif isinstance(level, str):
            level_map = {
                'DEBUG': LogLevel.DEBUG,
                'INFO': LogLevel.INFO,
                'NONE': LogLevel.NONE,
                None: LogLevel.NONE
            }
            self.level = level_map.get(level.upper() if level else None, LogLevel.DEBUG)
        else:
            self.level = LogLevel.NONE
    
    def _format_message(self, level_name, message):
        """Format log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{timestamp}] [{level_name}] {message}"
    
    def debug(self, message):
        """Log debug message."""
        if self.level.value >= LogLevel.DEBUG.value:
            print(self._format_message("DEBUG", message))
    
    def info(self, message):
        """Log info message."""
        if self.level.value >= LogLevel.INFO.value:
            print(self._format_message("INFO", message))
    
    def error(self, message):
        """Log error message."""
        print(self._format_message("ERROR", message))
