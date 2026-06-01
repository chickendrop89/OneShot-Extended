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

import argparse
import os

def parseArgs():
    """Parse arguments passed to the main python script."""

    parser = argparse.ArgumentParser(
        description='''
▄▖    ▄▖▌   ▗   ▄▖  ▗      ▌   ▌
▌▌▛▌█▌▚ ▛▌▛▌▜▘▄▖▙▖▚▘▜▘█▌▛▌▛▌█▌▛▌
▙▌▌▌▙▖▄▌▌▌▙▌▐▖  ▙▖▞▖▐▖▙▖▌▌▙▌▙▖▙▌

Copyright (C) 2026 chickendrop89
''',
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False
    )

    target_group = parser.add_argument_group('Required arguments')
    target_group.add_argument(
        '-i', '--interface',
        type=str,
        required=True,
        help='Name of the interface to use'
    )
    target_group.add_argument(
        '-b', '--bssid',
        type=str,
        help='BSSID of the target AP'
    )

    attack_group = parser.add_argument_group('Attack Modes')
    attack_pin_group = attack_group.add_mutually_exclusive_group()
    attack_pin_group.add_argument(
        '-p', '--pin',
        type=str,
        help='Use the specified pin (arbitrary string or 4/8 digit pin)'
    )
    attack_pin_group.add_argument(
        '-N', '--null-pin',
        action='store_true',
        help='Use a null pin'
    )
    attack_pin_group.add_argument(
        '-P', '--pixie-dust',
        action='store_true',
        help='Run Pixie Dust attack'
    )
    attack_pin_group.add_argument(
        '-B', '--bruteforce',
        action='store_true',
        help='Run online bruteforce attack'
    )
    attack_pin_group.add_argument(
        '--pbc', '--push-button-connect',
        action='store_true',
        help='Run WPS push button connection'
    )

    opt_group = parser.add_argument_group('Optional arguments')
    opt_group.add_argument(
        '-k', '--kill',
        action='store_true',
        help='Automatically kill processes interfering with the wireless interface'
    )
    opt_group.add_argument(
        '-r', '--restore',
        action='store_true',
        help='Restore killed interfering processes on exit (--kill)'
    )
    opt_group.add_argument(
        '-w', '--write',
        action='store_true',
        help='Write credentials to the file on success'
    )
    opt_group.add_argument(
        '-s', '--save',
        action='store_true',
        help='Save the AP to network manager on success'
    )
    opt_group.add_argument(
        '-l', '--loop',
        action='store_true',
        help='Run in a loop'
    )
    opt_group.add_argument(
        '-c', '--clear',
        action='store_true',
        help='Clear the screen on every wi-fi scan'
    )
    opt_group.add_argument(
        '-d', '--delay',
        type=float,
        default=0,
        help='Set a delay between pin attempts in seconds (default: %(default)s)'
    )
    opt_group.add_argument(
        '-t', '--timeout',
        type=float,
        default=60,
        help='Set the timeout for retrying after WPS lock (default: %(default)s)'
    )

    adv_group = parser.add_argument_group('Advanced Arguments')
    adv_group.add_argument(
        '-F', '--pixie-force',
        action='store_true',
        help='Run Pixiewps with --force option (bruteforce full range)'
    )
    adv_group.add_argument(
        '-S', '--show-pixie',
        action='store_true',
        help='Print pixiewps command and related data'
    )
    adv_group.add_argument(
        '-I', '--iface-down',
        action='store_true',
        help='Down network interface when the work is finished'
    )
    adv_group.add_argument(
        '-M', '--mtk-wifi',
        action='store_true',
        help='Activate MediaTek Wi-Fi interface driver on startup and deactivate it on exit'
    )
    adv_group.add_argument(
        '-D', '--dont-touch-settings',
        action='store_true',
        help="Don't touch the Android Wi-Fi settings on startup and exit"
    )
    adv_group.add_argument(
        '--reverse-scan',
        action='store_true',
        help='Reverse order of networks in the list of networks. Useful on small displays'
    )
    adv_group.add_argument(
        '--vuln-list',
        type=str,
        default=os.path.join(os.path.dirname(__file__), '../vulnwsc.txt'),
        help='Use custom file with vulnerable devices list'
    )
    adv_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose output'
    )
    adv_group.add_argument(
        '-h', '--help',
        action='help',
        help='Show this help message and exit'
    )

    args = parser.parse_args()

    if (args.pixie_force or args.show_pixie) and not args.pixie_dust:
        parser.error('argument -F/--pixie-force and -S/--show-pixie can only be used with -P/--pixie-dust')

    if args.delay and not args.bruteforce:
        parser.error('argument -d/--delay can only be used with -B/--bruteforce')

    if args.restore and not args.kill:
        parser.error('argument -r/--restore can only be used with -k/--kill')

    return args
