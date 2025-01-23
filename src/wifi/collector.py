import os
import subprocess
import csv

from datetime import datetime
from shutil import which

import src.wifi.android
import src.utils

class WiFiCollector:
    """Allows for collecting result, pin or network"""

    def __init__(self):
        self.ANDROID_NETWORK = src.wifi.android.AndroidNetwork()

    def write_result(self, bssid: str, essid: str, wps_pin: str, wpa_psk: str):
        reports_dir = src.utils.REPORTS_DIR
        filename = reports_dir + 'stored'
        write_table_header = not os.path.isfile(filename + '.csv')

        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir)

        date_str = datetime.now().strftime('%d.%m.%Y %H:%M')

        with open(filename + '.txt', 'a', encoding='utf-8') as file:
            # pylint: disable=consider-using-f-string
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

        print(f'[i] Credentials saved to {filename}.txt, {filename}.csv')


    def write_pin(self, bssid: str, pin: str):
        pixiewps_dir = src.utils.PIXIEWPS_DIR
        filename = pixiewps_dir + f'{bssid.replace(":", "").upper()}.run'

        with open(filename, 'w', encoding='utf-8') as file:
            file.write(pin)

        print(f'[i] PIN saved in {filename}')


    def add_network(self, bssid: str, essid: str, wpa_psk: str):
        # Split to three lines due to the length of the commands
        android_connect_cmd =(
            f'cmd -w wifi connect-network "{essid}" wpa2 "{wpa_psk}" -b "{bssid}"'
        )

        networkmanager_connect_cmd = (
            f'nmcli connection add type wifi con-name "{essid}" ssid "{essid}" wifi-sec.psk "{wpa_psk}" wifi-sec.key-mgmt wpa-psk'
        )

        # Detect standard android system
        if src.utils.isAndroid() is True:
            self.ANDROID_NETWORK.enableWifi(force_enable=True)
            subprocess.run(android_connect_cmd,
                shell=True
            )
            self.ANDROID_NETWORK.disableWifi(force_disable=True)

        # Detect NetworkManager
        if which('nmcli'):
            subprocess.run(networkmanager_connect_cmd,
                shell=True
            )

        print('[i] Access Point was saved to your network manager')
