import subprocess
import time

import src.utils

class AndroidNetwork:
    """Disable or Enable android Wi-Fi-related settings"""

    def __init__(self):
        self.INTERFACE = None
        self.ENABLED_SCANNING = 0

    def __getActiveInterface(self):
        getprop_cmd = 'getprop wifi.interface'

        active_wifi_interface = subprocess.run(getprop_cmd,
            shell=True, text=True,
            capture_output=True
        )

        if active_wifi_interface.stdout == '':
            src.utils.die('[!] Could not determine active android Wi-Fi interface')

        self.INTERFACE = active_wifi_interface

    def storeAlwaysScanState(self):
        """Stores Initial Wi-Fi 'always-scanning' state, so it can be restored on exit"""

        settings_cmd = 'settings get global wifi_scan_always_enabled'

        is_scanning_on = subprocess.check_output(settings_cmd,
            shell=True, text=True
        )
        is_scanning_on = is_scanning_on.strip()

        if is_scanning_on == '1':
            self.ENABLED_SCANNING = 1

    def disableWifi(self, force_disable: bool = False):
        """Disable Wi-Fi connectivity on Android"""

        self.__getActiveInterface()

        ip_link_cmd = f'ip link set {self.INTERFACE} down && ip link set {self.INTERFACE} up'
        wifi_disable_scanning_cmd = 'cmd -w wifi enable-scanning disabled'
        wifi_disable_always_scanning_cmd = 'cmd -w wifi set-scan-always-available disabled'

        # This tricks the Android Wi-Fi scanner to temporarily stop
        subprocess.run(ip_link_cmd,
            shell=True
        )
        subprocess.run(wifi_disable_scanning_cmd,
            shell=True
        )

        # Always scanning for networks (for location/service purposes) confuses wpa_supplicant
        if self.ENABLED_SCANNING == 1 or force_disable is True:
            subprocess.run(wifi_disable_always_scanning_cmd, shell=True)

        time.sleep(2.5)

    def enableWifi(self, force_enable: bool = False):
        """Enable Wi-Fi connectivity on Android"""

        wifi_enable_scanning_cmd = 'cmd -w wifi enable-scanning enabled'
        wifi_enable_always_scanning_cmd = 'cmd -w wifi set-scan-always-available enabled'
        wifi_start_scan_cmd = 'cmd -w wifi start-scan'

        # Make the Android Wi-Fi scanner work again
        subprocess.run(wifi_enable_scanning_cmd,
            shell=True
        )
        subprocess.run(wifi_start_scan_cmd,
            shell=True
        )

        if self.ENABLED_SCANNING == 1 or force_enable is True:
            subprocess.run(wifi_enable_always_scanning_cmd, shell=True)
