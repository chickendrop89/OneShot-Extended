import sys
import os
import pathlib
import subprocess

USER_HOME = str(pathlib.Path.home())
SESSIONS_DIR = f'{USER_HOME}/.OneShot/sessions/'
PIXIEWPS_DIR = f'{USER_HOME}/.OneShot/pixiewps/'
REPORTS_DIR = os.path.dirname(os.path.realpath(__file__)) + '/reports/'

def getHex(line: str):
    a = line.split(':', 3)
    return a[2].replace(' ', '').upper()

def isAndroid():
    return bool(hasattr(sys, 'getandroidapilevel'))

def ifaceUp(interface: str, down: bool = False):
    if down:
        action = 'down'
    else:
        action = 'up'

    cmd = f'ip link set {interface} {action}'

    res = subprocess.run(cmd,
        shell=True, stdout=sys.stdout, stderr=sys.stdout
    )

    return not res.returncode

def die(text: str):
    sys.stderr.write(text + '\n')
    sys.exit(1)
