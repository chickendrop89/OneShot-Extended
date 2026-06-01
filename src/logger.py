#  OneShot-Extended (WPS penetration testing utility) is a fork of the tool with extra features
#  Copyright (C) 2026 chickendrop89
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

_LOGGER = None

class _ColorFormatter(logging.Formatter):
    """Custom formatter that adds colored log level prefixes"""

    COLORS = {
        '[*]': '\033[0;32m',  # Dark Green
        '[+]': '\033[1;32m',  # Bold Green
        '[-]': '\033[1;33m',  # Bold Yellow
        '[!]': '\033[1;31m',  # Bold Red
        'RESET': '\033[0m'
    }

    LEVEL_PREFIXES = {
        logging.INFO: '[*]',
        logging.WARNING: '[-]',
        logging.ERROR: '[!]',
        logging.CRITICAL: '[!]',
    }

    def format(self, record):
        msg_str = str(record.msg)

        prefix = self.LEVEL_PREFIXES.get(record.levelno, '[*]')
        for pfx in ['[*]', '[+]', '[-]', '[!]']:
            if msg_str.startswith(pfx):
                prefix = pfx
                record.msg = msg_str[len(pfx):].lstrip()
                break

        color = self.COLORS.get(prefix, '')
        reset = self.COLORS['RESET']
        record.msg = f"{color}{prefix}{reset} {record.msg}"

        return super().format(record)

def _getLogger(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    """Get a configured logger instance"""

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(level)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)

        formatter = _ColorFormatter(fmt='%(message)s')
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger

def initializeLogging():
    """Initialize the global logging system"""

    global _LOGGER # pylint: disable=global-statement

    _LOGGER = _getLogger('ose', logging.INFO)

def info(message: str):
    """Log an info message"""

    if _LOGGER is None:
        initializeLogging()

    _LOGGER.info(message)

def success(message: str):
    """Log a success message (uses [+] prefix)"""

    if _LOGGER is None:
        initializeLogging()

    # We need to manually add [+] since logging doesn't have a SUCCESS level
    _LOGGER.info('[+] %s', message)

def warning(message: str):
    """Log a warning message"""

    if _LOGGER is None:
        initializeLogging()

    _LOGGER.warning(message)

def error(message: str):
    """Log an error message"""

    if _LOGGER is None:
        initializeLogging()

    _LOGGER.error(message)
