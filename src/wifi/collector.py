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

import os
import subprocess
import csv

from datetime import datetime
from shutil import which

import src.wifi.android
import src.utils

class WiFiCollector:
    """Allows for collecting result, pin or network."""

    def __init__(self):
        self.ANDROID_NETWORK = src.wifi.android.AndroidNetwork()

    def addNetwork(self, bssid: str, essid: str, wpa_psk: str):
        """Ads a network to systems network manager."""

        android_connect_cmd = ['cmd']
        android_connect_cmd.extend([
            '-w', 'wifi',
            'connect-network', f"{essid}",
            'wpa2', f"{wpa_psk}", 
            '-b', f"{bssid}"
        ])

        networkmanager_connect_cmd = ['nmcli']
        networkmanager_connect_cmd.extend([
            'connection', 'add', 
            'type', 'wifi', 
            'con-name', f"{essid}",
            'ssid', f"{essid}", 
            'wifi-sec.psk', f"{wpa_psk}",
            'wifi-sec.key-mgmt', 'wpa-psk'
        ])

        # Detect an android system
        if src.utils.isAndroid() is True:
            try:
                # The Wi-Fi scanner needs to be active in order to add network
                self.ANDROID_NETWORK.enableWifi(force_enable=True, whisper=True)
                subprocess.run(android_connect_cmd, check=True)
            except subprocess.CalledProcessError as error:
                return print(f'[!] Failed to add network to Android network manager: \n {error}')

        # Detect NetworkManager
        elif which('nmcli'):
            try:
                subprocess.run(networkmanager_connect_cmd, check=True)
            except subprocess.CalledProcessError as error:
                return print(f'[!] Failed to add network to NetworkManager: \n {error}')


        print('[+] Access Point was saved to your network manager')

    @staticmethod
    def writeResult(bssid: str, essid: str, wps_pin: str, wpa_psk: str):
        """Writes the success result to a stored.{txt,csv} file."""
        #TODO: The same result can be written multiple times

        reports_dir = src.utils.REPORTS_DIR
        filename = reports_dir + 'stored'

        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        write_table_header = not os.path.isfile(filename + '.csv')
        date_str = datetime.now().strftime('%d.%m.%Y %H:%M')

        with open(filename + '.txt', 'a', encoding='utf-8') as file:
            file.write('{}\nBSSID: {}\nESSID: {}\nWPS PIN: {}\nWPA PSK: {}\n\n'.format(
                date_str, bssid, essid, wps_pin, wpa_psk
            ))

        with open(filename + '.csv', 'a', newline='', encoding='utf-8') as file:
            csv_writer = csv.writer(file,
                delimiter=';', quoting=csv.QUOTE_ALL
            )

            if write_table_header:
                csv_writer.writerow(['Date', 'BSSID', 'ESSID', 'WPS PIN', 'WPA PSK'])

            csv_writer.writerow([date_str, bssid, essid, wps_pin, wpa_psk])

        print(f'[+] Credentials saved to {filename}.txt, {filename}.csv')

    @staticmethod
    def writePin(bssid: str, pin: str):
        """Writes PIN to a file for later use."""

        pixiewps_dir = src.utils.PIXIEWPS_DIR
        filename = f'''{pixiewps_dir}{bssid.replace(':', '').upper()}.run'''

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(pin)

        print(f'[+] PIN saved in {filename}')
