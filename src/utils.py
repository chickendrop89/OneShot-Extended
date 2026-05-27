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
import json
import pathlib
import subprocess
import time

from shutil import which
from src import logger

USER_HOME = str(pathlib.Path.home())
SESSIONS_DIR = f'{USER_HOME}/.OneShot-Extended/sessions/'
PIXIEWPS_DIR = f'{USER_HOME}/.OneShot-Extended/pixiewps/'
REPORTS_DIR  = f'{os.getcwd()}/reports/'

def _getInterferingProcesses():
    """Get a list of processes actively using the generic netlink subsystem."""

    try:
        with open('/proc/net/netlink', 'r', encoding='utf-8') as f:
            next(f)

            tokens = (line.split() for line in f)
            pids = {int(p[2]) for p in tokens if len(p) > 2 and p[1] == '16'}

            pids.discard(os.getpid())
    except IOError:
        return []

    interfering_pids = []
    for pid in pids:
        try:
            fd_entries = os.scandir(f'/proc/{pid}/fd')
            has_socket = any('socket' in os.readlink(e.path) for e in fd_entries)

            if has_socket:
                with open(f'/proc/{pid}/comm', 'r', encoding='utf-8') as f_comm:
                    pname = f_comm.read().strip()

                    interfering_pids.append((pid, pname))
        except OSError:
            continue

    return interfering_pids

def _saveKilledProcesses(processes: list[tuple[int, str, str]]):
    """Save killed process information to a file for restoration."""

    if not processes:
        return

    try:
        killed_file = os.path.join(SESSIONS_DIR, 'killed_processes.json')

        with open(killed_file, 'w', encoding='utf-8') as f:
            json.dump(processes, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save killed processes: {e}")

def _getProcessCommand(pid: int) -> str:
    """Get the command line of a process from /proc."""

    try:
        with open(f'/proc/{pid}/cmdline', 'r', encoding='utf-8') as f:
            cmdline = f.read().replace('\0', ' ').strip()

            return cmdline
    except OSError:
        return ''

def checkRunningProcesses(interface: str):
    """Detect and warn about other processes actively using the generic netlink subsystem."""

    interfering_pids = _getInterferingProcesses()

    if interfering_pids:
        processes_str = ', '.join([f"{pname} (PID {pid})" for pid, pname in interfering_pids])
        logger.warning(f"Another process is using the {interface} interface: {processes_str}")

def killInterfering():
    """Kill all processes actively using the generic netlink subsystem."""

    interfering_pids = _getInterferingProcesses()
    killed_processes = []

    if interfering_pids:
        for pid, pname in interfering_pids:
            try:
                cmdline = _getProcessCommand(pid)
                os.kill(pid, 15)
                logger.warning(f"Terminated process {pname} (PID {pid})")
                killed_processes.append((pid, pname, cmdline))

                # Give time to release locks
                time.sleep(1.5)
            except OSError as e:
                logger.error(f"Failed to terminate {pname} (PID {pid}): {e}")

        _saveKilledProcesses(killed_processes)

def restoreProcesses():
    """Restore processes that were previously killed."""

    killed_file = os.path.join(SESSIONS_DIR, 'killed_processes.json')

    if not os.path.exists(killed_file):
        return

    try:
        with open(killed_file, 'r', encoding='utf-8') as f:
            killed_processes = json.load(f)
    except (IOError, json.JSONDecodeError) as e:
        logger.error(f"Failed to read killed processes file: {e}")
        return

    for pid, pname, cmdline in killed_processes:
        if not cmdline:
            logger.warning(f"Cannot restore {pname} (PID {pid}): command line not available")
            continue

        try:
            subprocess.Popen(cmdline,
                shell=True, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"Restored process {pname}")
        except (OSError, subprocess.CalledProcessError) as e:
            logger.error(f"Failed to restore {pname}: {e}")

    try:
        os.remove(killed_file)
    except OSError:
        pass

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

            if not which(rfkill_command[0]):
                logger.warning('rfkill utility is not available, unable to do anything')
                return

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

def addVulnerableAP(network_info: dict, vuln_list_file: str):
    """Add vulnerable device model/name to the vulnerable APs list."""

    if not network_info:
        return

    model = network_info.get('Model', '').strip()
    model_number = network_info.get('Model number', '').strip()
    device_name = network_info.get('Device name', '').strip()

    vuln_entry = None

    if model:
        vuln_entry = f'{model} {model_number}'.strip() if model_number else model
    elif device_name:
        vuln_entry = device_name

    if not vuln_entry:
        logger.warning('No model or device name information available to save')
        return

    try:
        # Check if entry already exists in the list
        try:
            with open(vuln_list_file, 'r', encoding='utf-8') as f:
                existing_entries = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            existing_entries = []

        if vuln_entry in existing_entries:
            logger.info(f'Device {vuln_entry} is already in the vulnerable list')
            return

        # Append entry to the vulnerable list
        with open(vuln_list_file, 'a', encoding='utf-8') as f:
            f.write(f'{vuln_entry}\n')
            logger.info(f'Added {vuln_entry} to vulnerable list')
    except IOError as e:
        logger.error(f'Failed to save to vulnerable list: {e}')

def isAndroid():
    """Check if this project is ran on android."""

    return bool(hasattr(sys, 'getandroidapilevel'))

def clearScreen():
    """Clear the terminal screen."""

    sys.stdout.write('\033[H\033[2J')
    sys.stdout.flush()

def die(text: str):
    """Print an error and exit with non-zero exit code."""

    sys.exit(f'[!] {text} \n')
