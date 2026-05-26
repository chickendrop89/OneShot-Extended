#  OneShot-Extended (WPS penetration testing utility) is a fork of the tool with extra features
#  Copyright (C) 2025 chickendrop89
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

import logging
import sys

class ColorFormatter(logging.Formatter):
    """Custom formatter that adds log level prefixes in the format"""

    LEVEL_PREFIXES = {
        logging.DEBUG: '[*]',
        logging.INFO: '[*]',
        logging.WARNING: '[-]',
        logging.ERROR: '[!]',
        logging.CRITICAL: '[!]',
    }

    def format(self, record):
        prefix = self.LEVEL_PREFIXES.get(record.levelno, '[*]')

        if record.msg:
            # Avoid double prefixes if the message already has one
            if not str(record.msg).startswith(('[*]', '[+]', '[-]', '[!]')):
                record.msg = f'{prefix} {record.msg}'

        return super().format(record)

# pylint: disable=invalid-name
def get_logger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger instance"""

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = ColorFormatter(fmt='%(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger

_logger = None

# pylint: disable=invalid-name
def initialize_logging(verbose: bool = False):
    """Initialize the global logging system"""

    global _logger # pylint: disable=global-statement
    level = logging.DEBUG if verbose else logging.INFO

    _logger = get_logger('ose', level)

def info(message: str):
    """Log an info message"""

    if _logger is None:
        initialize_logging()

    _logger.info(message)

def success(message: str):
    """Log a success message (uses [+] prefix)"""

    if _logger is None:
        initialize_logging()

    # We need to manually add [+] since logging doesn't have a SUCCESS level
    _logger.info('[+] %s', message)

def warning(message: str):
    """Log a warning message"""

    if _logger is None:
        initialize_logging()

    _logger.warning(message)

def error(message: str):
    """Log an error message"""

    if _logger is None:
        initialize_logging()

    _logger.error(message)

def debug(message: str):
    """Log a debug message"""

    if _logger is None:
        initialize_logging()

    _logger.debug(message)
