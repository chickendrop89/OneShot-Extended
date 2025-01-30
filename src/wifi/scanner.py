import os
import re
import csv
import codecs
import subprocess

from src.utils import REPORTS_DIR

import src.args
args = src.args.parseArgs()

class WiFiScanner:
    """Handles parsing scan results and table."""

    def __init__(self, interface: str, vuln_list: str = None):
        self.INTERFACE = interface
        self.VULN_LIST = vuln_list

        reports_fname = REPORTS_DIR + 'stored.csv'

        try:
            # Look for already stored networks to highlight
            with open(reports_fname, 'r', newline='', encoding='utf-8') as file:
                csv_reader = csv.reader(file,
                    delimiter=';', quoting=csv.QUOTE_ALL
                )

                # Skip header
                next(csv_reader)
                self.STORED = []

                for row in csv_reader:
                    self.STORED.append(
                        (
                            row[1],   # BSSID
                            row[2]    # ESSID
                        )
                    )
        except FileNotFoundError:
            self.STORED = []

    def promptNetwork(self) -> str:
        """Prompts the user to select a network from the available WPS networks."""

        networks = self._iwScanner()

        if not networks:
            print('[-] No WPS networks found.')
            return

        while True:
            try:
                network_no = input('Select target (press Enter to refresh): ')

                if network_no.lower() in {'r', '0', ''}:
                    if args.clear:
                        src.utils.clearScreen()
                    return self.promptNetwork()

                if int(network_no) in networks.keys():
                    return networks[int(network_no)]['BSSID']

                raise IndexError
            except IndexError:
                print('Invalid number')

    def _iwScanner(self) -> dict[int, dict] | bool:
        """Parsing iw scan results."""

        def handleNetwork(_line, result, networks):
            networks.append(
                {
                    'Security type': 'Unknown',
                    'WPS': False,
                    'WPS version': '1.0',
                    'WPS locked': False,
                    'Model': '',
                    'Model number': '',
                    'Device name': ''
                }
            )
            networks[-1]['BSSID'] = result.group(1).upper()

        def handleEssid(_line, result, networks):
            d = result.group(1)
            networks[-1]['ESSID'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handleLevel(_line, result, networks):
            networks[-1]['Level'] = int(float(result.group(1)))

        def handleSecurityType(_line, result, networks):
            sec = networks[-1]['Security type']
            if result.group(1) == 'capability':
                if 'Privacy' in result.group(2):
                    sec = 'WEP'
                else:
                    sec = 'Open'
            elif sec == 'WEP':
                if result.group(1) == 'RSN':
                    sec = 'WPA2'
                elif result.group(1) == 'WPA':
                    sec = 'WPA'
            elif sec == 'WPA':
                if result.group(1) == 'RSN':
                    sec = 'WPA/WPA2'
            elif sec == 'WPA2':
                if result.group(1) == 'PSK SAE':
                    sec = 'WPA2/WPA3'
                elif result.group(1) == 'WPA':
                    sec = 'WPA/WPA2'
            networks[-1]['Security type'] = sec

        def handleWps(_line, result, networks):
            is_wps_enabled = bool(result.group(1))
            networks[-1]['WPS'] = is_wps_enabled

        def handleWpsVersion(_line, result, networks):
            wps_ver = networks[-1]['WPS version']

            # Only WPS 2.0 APs broadcast this, this way we can distinguish between 1.0<->2.0
            wps_ver_filtered = result.group(1).replace('* Version2:', '')

            if wps_ver_filtered == '2.0':
                wps_ver = '2.0'

            networks[-1]['WPS version'] = wps_ver

        def handleWpsLocked(_line, result, networks):
            flag = int(result.group(1), 16)
            if flag:
                networks[-1]['WPS locked'] = True

        def handleModel(_line, result, networks):
            d = result.group(1)
            networks[-1]['Model'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handleModelNumber(_line: str, result: str, networks: list):
            d = result.group(1)
            networks[-1]['Model number'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        def handleDeviceName(_line, result, networks):
            d = result.group(1)
            networks[-1]['Device name'] = codecs.decode(d, 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')

        networks = []
        matchers = {
            re.compile(r'BSS (\S+)( )?\(on \w+\)'): handleNetwork,
            re.compile(r'SSID: (.*)'): handleEssid,
            re.compile(r'signal: ([+-]?([0-9]*[.])?[0-9]+) dBm'): handleLevel,
            re.compile(r'(capability): (.+)'): handleSecurityType,
            re.compile(r'(RSN):\t [*] Version: (\d+)'): handleSecurityType,
            re.compile(r'(WPA):\t [*] Version: (\d+)'): handleSecurityType,
            re.compile(r'WPS:\t [*] Version: (([0-9]*[.])?[0-9]+)'): handleWps,
            re.compile(r' [*] Version2: (.+)'): handleWpsVersion,
            re.compile(r' [*] Authentication suites: (.+)'): handleSecurityType,
            re.compile(r' [*] AP setup locked: (0x[0-9]+)'): handleWpsLocked,
            re.compile(r' [*] Model: (.*)'): handleModel,
            re.compile(r' [*] Model Number: (.*)'): handleModelNumber,
            re.compile(r' [*] Device name: (.*)'): handleDeviceName
        }

        command = ['iw', 'dev', f'{self.INTERFACE}', 'scan']
        iw_scan_process = subprocess.run(command,
            encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )

        lines = iw_scan_process.stdout.splitlines()

        for line in lines:
            if line.startswith('command failed:'):
                print('[!] Error:', line)
                return False

            line = line.strip('\t')

            for regexp, handler in matchers.items():
                res = re.match(regexp, line)
                if res:
                    handler(line, res, networks)

        # Filtering non-WPS networks
        networks = list(filter(lambda x: bool(x['WPS']), networks))

        if not networks:
            return False

        # Sorting by signal level
        networks.sort(key=lambda x: x['Level'], reverse=True)

        # Putting a list of networks in a dictionary, where each key is a network number in list of networks
        network_list = {(i + 1): network for i, network in enumerate(networks)}
        network_list_items = list(network_list.items())

        def truncateStr(s: str, length: int, postfix='…') -> str:
            """Truncate string with the specified length."""

            if len(s) > length:
                k = length - len(postfix)
                s = s[:k] + postfix
            return s

        def colored(text: str, color: str) -> str:
            """Returns colored text"""

            if color:
                if color == 'green':
                    text = f'\033[1m\033[92m{text}\033[00m'
                if color == 'dark_green':
                    text = f'\033[32m{text}\033[00m'
                elif color == 'red':
                    text = f'\033[1m\033[91m{text}\033[00m'
                elif color == 'yellow':
                    text = f'\033[1m\033[93m{text}\033[00m'
                else:
                    return text
            else:
                return text
            return text

        print('Network marks: {1} {0} {2} {0} {3} {0} {4}'.format(
            '|',
            colored('Vulnerable model', color='green'),
            colored('Vulnerable WPS ver.', color='dark_green'),
            colored('WPS locked', color='red'),
            colored('Already stored', color='yellow')
        ))

        def entryMaxLength(item: str, max_length=27) -> int:
            """Calculates max length of network_list_items entry"""

            lengths = [len(entry[1][item]) for entry in network_list_items]
            return min(max(lengths), max_length) + 1

        # Used to calculate the max width of a collum in the network list table
        columm_lengths = {
            '#': 4,
            'sec': entryMaxLength('Security type'),
            'bssid': 18,
            'essid': entryMaxLength('ESSID'),
            'name': entryMaxLength('Device name'),
            'model': entryMaxLength('Model')
        }

        row = '{:<{#}} {:<{bssid}} {:<{essid}} {:<{sec}} {:<{#}} {:<{#}} {:<{name}} {:<{model}}'

        print(row.format(
            '#', 'BSSID', 'ESSID', 'Sec.', 'PWR', 'Ver.', 'WSC name', 'WSC model',
            **columm_lengths
        ))

        if args.reverse_scan:
            network_list_items = network_list_items[::-1]
        for n, network in network_list_items:
            number = f'{n})'
            model = f'{network['Model']} {network['Model number']}'
            essid = truncateStr(network['ESSID'], 25)
            device_name = truncateStr(network['Device name'], 27)
            line = row.format(
                number, network['BSSID'], essid,
                network['Security type'], network['Level'],
                network['WPS version'], device_name, model,
                **columm_lengths
            )
            if (network['BSSID'], network['ESSID']) in self.STORED:
                print(colored(line, color='yellow'))
            elif network['WPS version'] == '1.0':
                print(colored(line, color='dark_green'))
            elif network['WPS locked']:
                print(colored(line, color='red'))
            elif self.VULN_LIST and (model in self.VULN_LIST) or (device_name in self.VULN_LIST):
                print(colored(line, color='green'))
            else:
                print(line)

        return network_list
