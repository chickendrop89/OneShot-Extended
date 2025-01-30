import subprocess
import time

class AndroidNetwork:
    """Manages android Wi-Fi-related settings"""

    def __init__(self):
        self.ENABLED_SCANNING = 0

    def storeAlwaysScanState(self):
        """Stores Initial Wi-Fi 'always-scanning' state, so it can be restored on exit"""

        settings_cmd = ['settings', 'get', 'global', 'wifi_scan_always_enabled']

        is_scanning_on = subprocess.run(settings_cmd,
            encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True
        )
        is_scanning_on = is_scanning_on.stdout.strip()

        if is_scanning_on == '1':
            self.ENABLED_SCANNING = 1

    def disableWifi(self, force_disable: bool = False, whisper: bool = False):
        """Disable Wi-Fi connectivity on Android."""

        if whisper is False:
            print('[*] Android: disabling Wi-Fi')

        wifi_disable_scanner_cmd = ['cmd', 'wifi', 'set-wifi-enabled', 'disabled']
        wifi_disable_always_scanning_cmd = ['cmd', '-w', 'wifi', 'set-scan-always-available', 'disabled']

        # Disable Android Wi-Fi scanner
        subprocess.run(wifi_disable_scanner_cmd)

        # Always scanning for networks causes the interface to be occupied by android
        if self.ENABLED_SCANNING == 1 or force_disable is True:
            subprocess.run(wifi_disable_always_scanning_cmd)

        time.sleep(3)

    def enableWifi(self, force_enable: bool = False, whisper: bool = False):
        """Enable Wi-Fi connectivity on Android."""

        if whisper is False:
            print('[*] Android: enabling Wi-Fi')

        wifi_enable_scanner_cmd = ['cmd', 'wifi', 'set-wifi-enabled', 'enabled']
        wifi_enable_always_scanning_cmd = ['cmd', '-w', 'wifi', 'set-scan-always-available', 'enabled']

        # Enable Android Wi-Fi scanner
        subprocess.run(wifi_enable_scanner_cmd)

        if self.ENABLED_SCANNING == 1 or force_enable is True:
            subprocess.run(wifi_enable_always_scanning_cmd)
