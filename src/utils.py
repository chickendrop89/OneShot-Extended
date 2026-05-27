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

import sys
import os
import pathlib
import subprocess

from src import logger

USER_HOME = str(pathlib.Path.home())
SESSIONS_DIR = f'{USER_HOME}/.OneShot-Extended/sessions/'
PIXIEWPS_DIR = f'{USER_HOME}/.OneShot-Extended/pixiewps/'
REPORTS_DIR  = f'{os.getcwd()}/reports/'

def isAndroid():
    """Check if this project is ran on android."""

    return bool(hasattr(sys, 'getandroidapilevel'))

def ifaceCtl(interface: str, action: str):
    """Put an interface up or down."""

    command = ['ip', 'link', 'set', f'{interface}', f'{action}']

    try:
        command_output = subprocess.run(command,
            encoding='utf-8', stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as error:
        logger.error(f'Can not control interface with ip link: \n {error}')

    command_output_stripped = command_output.stdout.strip()

    if isAndroid() is False:
        def _rfKillUnblock():
            rfkill_command = ['rfkill', 'unblock', 'wifi']

            try:
                subprocess.run(rfkill_command, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as error:
                logger.error(f'Failed to unblock interface, not continuing: \n {error}')

        if 'RF-kill' in command_output_stripped:
            logger.warning('RF-kill is blocking the interface, unblocking')
            _rfKillUnblock()
            return

    if command_output.returncode != 0:
        logger.error(command_output_stripped)

    return command_output.returncode

def isInterfaceUp(interface: str) -> bool:
    """Check if the network interface is still up."""

    try:
        command = ['ip', 'link', 'show', interface]
        output = subprocess.run(command,
            encoding='utf-8', stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=5
        )

        if output.returncode != 0:
            return False

        if 'UP' in output.stdout:
            return True

        return False

    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False

def clearScreen():
    """Clear the terminal screen."""

    sys.stdout.write('\033[H\033[2J')
    sys.stdout.flush()

def die(text: str):
    """Print an error and exit with non-zero exit code."""

    sys.exit(f'[!] {text} \n')
