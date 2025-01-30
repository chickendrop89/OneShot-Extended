import sys
import os
import pathlib
import subprocess

USER_HOME = str(pathlib.Path.home())
SESSIONS_DIR = f'{USER_HOME}/.OSE/sessions/'
PIXIEWPS_DIR = f'{USER_HOME}/.OSE/pixiewps/'
REPORTS_DIR  = f'{os.getcwd()}/reports/'

def isAndroid():
    """Check if this project is ran on android."""

    return bool(hasattr(sys, 'getandroidapilevel'))

def ifaceCtl(interface: str, action: str):
    """Put an interface up or down."""

    command = ['ip', 'link', 'set', f'{interface}', f'{action}']
    command_output = subprocess.run(command)

    return not command_output.returncode

def clearScreen():
    """Clear the terminal screen."""

    os.system('clear')

def die(text: str):
    """Print an error and exit with non-zero exit code."""

    sys.exit(f'[!] {text} \n')
