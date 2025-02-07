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
    command_output = subprocess.run(
        command, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    command_output_stripped = command_output.stdout.strip()

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
