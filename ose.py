#!/usr/bin/env python3

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

import os
import sys

# pylint: disable=wrong-import-position
if sys.version_info < (3, 10):
    sys.exit('Python 3.10 or higher is required to run this script.')

from shutil import which
from pathlib import Path
from src import logger

import src.wifi.android
import src.wifi.scanner
import src.wps.connection
import src.wps.bruteforce
import src.utils
import src.args

def checkRequirements():
    """Verify requirements are met"""

    required_binaries = [
        'pixiewps',
        'wpa_supplicant',
        'iw', 'ip'
    ]
    missing = [b for b in required_binaries if not which(b)]

    if missing:
        src.utils.die(f"Missing required utilities: {', '.join(missing)}")

    if os.getuid() != 0:
        src.utils.die('Run it as root')

def setupDirectories():
    """Create required directories"""

    # We recently changed the PIXIEWPS_DIR and SESSIONS_DIR path
    # Rename older .OSE data dir to .OneShot-Extended, and maintain compatibility
    old_dir = os.path.expanduser('~/.OSE')
    new_dir = os.path.expanduser('~/.OneShot-Extended')

    if os.path.exists(old_dir):
        try:
            os.rename(old_dir, new_dir)
            logger.info('Renamed legacy data directory')
        except OSError as e:
            logger.error(f'Failed to rename data directory: {e}')

    for directory in [src.utils.SESSIONS_DIR, src.utils.PIXIEWPS_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

def setupAndroidWifi(android_network: src.wifi.android.AndroidNetwork, enable: bool = False):
    """Configure Android-specific WiFi settings"""

    if enable:
        android_network.enableWifi()
    else:
        android_network.storeAlwaysScanState()
        android_network.disableWifi()

def setupMediatekWifi(wmt_wifi_device: Path):
    """Initialize MediaTek WiFi dev"""

    if not wmt_wifi_device.is_char_device():
        src.utils.die('Unable to activate MediaTek Wi-Fi interface device (--mtk-wifi): '
                     '/dev/wmtWifi does not exist or it is not a character device')

    wmt_wifi_device.chmod(0o644)
    wmt_wifi_device.write_text('1', encoding='utf-8')


def scanForNetworks(interface: str, vuln_list: list[str]) -> str:
    """Scan, and prompt user to select network. Returns BSSID"""

    scanner = src.wifi.scanner.WiFiScanner(interface, vuln_list)
    return scanner.promptNetwork()

def handleConnection(args):
    """Main connection logic"""

    network_info = {}
    success = False

    if args.bruteforce:
        connection = src.wps.bruteforce.Initialize(args.interface)
    else:
        connection = src.wps.connection.Initialize(args.interface)

    if args.pbc:
        connection.singleConnection(pbc_mode=True)
    else:
        if not args.bssid:
            try:
                with open(args.vuln_list, 'r', encoding='utf-8') as file:
                    vuln_list = file.read().splitlines()
            except FileNotFoundError:
                vuln_list = []

            if not args.loop:
                logger.info('BSSID not specified (--bssid) — scanning for available networks')

            args.bssid, network_info = scanForNetworks(
                args.interface, vuln_list
            )

        if args.bssid:
            if args.bruteforce:
                connection.smartBruteforce(
                    args.bssid,
                    args.pin
                )
            else:
                success = connection.singleConnection(
                    args.bssid,
                    args.pin
                )

                if args.pin and connection.CONNECTION_STATUS.IS_LOCKED:
                    logger.warning(f'{args.bssid} is WPS LOCKED')

            # Save to vulnerable list
            if success and args.pixie_dust and network_info:
                src.utils.addVulnerableAP(network_info, args.vuln_list)

def main():
    """Main os-e code"""

    checkRequirements()
    setupDirectories()

    args = src.args.parseArgs()
    logger.initialize_logging(verbose=args.verbose)

    src.utils.checkRunningProcesses(args.interface)

    if args.kill:
        src.utils.killInterfering()

    while True:
        try:
            android_network = src.wifi.android.AndroidNetwork()

            if args.clear:
                src.utils.clearScreen()

            if src.utils.isAndroid() is True and not args.dts and not args.mtk_wifi:
                setupAndroidWifi(android_network)

            if args.mtk_wifi:
                wmt_wifi_device = Path('/dev/wmtWifi')
                setupMediatekWifi(wmt_wifi_device)

            if src.utils.ifaceCtl(args.interface, action='up'):
                src.utils.die(f'Unable to up interface \'{args.interface}\'')

            handleConnection(args)

            if not args.loop:
                break

            args.bssid = None

        except KeyboardInterrupt:
            if args.loop:
                if input('\n[?] Exit the script (otherwise continue to AP scan)? [N/y] ').lower() == 'y':
                    logger.info('Aborting…')
                    break
                args.bssid = None
            else:
                logger.info('Aborting…')
                break

        finally:
            if src.utils.isAndroid() is True and not args.dts and not args.mtk_wifi:
                setupAndroidWifi(android_network, enable=True)

    if args.iface_down:
        src.utils.ifaceCtl(args.interface, action='down')

    if args.mtk_wifi:
        wmt_wifi_device.write_text('0', encoding='utf-8')

    if args.restore:
        src.utils.restoreProcesses()

if __name__ == '__main__':
    main()
