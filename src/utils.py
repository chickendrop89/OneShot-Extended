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

import sys
import os
import pathlib
import subprocess

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
    command_output = subprocess.run(
        command, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    command_output_stripped = command_output.stdout.strip()
    
    # Fix "RNETLINK: No such device" issues on specific android devices
    if isAndroid() is False:
        def _rfKillUnblock():
            rfkill_command = ['rfkill', 'unblock', 'wifi']
            subprocess.run(rfkill_command, check=True)

        if 'RF-kill' in command_output_stripped:
            print('[!] RF-kill is blocking the interface, unblocking')
            _rfKillUnblock()  # Will throw CalledProcessError if fails
            return 0

    if command_output.returncode != 0:
        print(f'[!] {command_output_stripped}')

    return command_output.returncode

def clearScreen():
    """Clear the terminal screen."""

    os.system('clear')

def die(text: str):
    """Print an error and exit with non-zero exit code."""

    sys.exit(f'[!] {text} \n')
