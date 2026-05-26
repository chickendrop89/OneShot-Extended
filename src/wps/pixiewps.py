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

import subprocess

from typing import Union
from src import logger

class Data:
    """Stored data used for pixiewps command."""

    def __init__(self):
        self.PKE = ''
        self.PKR = ''
        self.E_HASH1 = ''
        self.E_HASH2 = ''
        self.AUTHKEY = ''
        self.E_NONCE = ''
        self.R_NONCE = ''
        self.BSSID = ''

    def getAll(self):
        """Output all pixiewps related variables."""

        return all([self.PKE, self.PKR, self.E_NONCE, self.R_NONCE, self.AUTHKEY, self.E_HASH1, self.E_HASH2, self.BSSID])

    def runPixieWps(self, show_command: bool = False, full_range: bool = False) -> Union[str, bool]:
        """Runs the pixiewps and attempts to extract the WPS pin from the output."""

        logger.info('Running Pixiewps…')
        command = self._getPixieCmd(full_range)

        if show_command:
            # Convert the command array into a string
            logger.debug(' '.join(command))

        try:
            command_output = subprocess.run(command,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding='utf-8'
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as error:
            logger.error(f'Pixiewps has exited on error: \n {error}')
            return False

        logger.info(command_output.stdout)

        if command_output.returncode == 0:
            lines = command_output.stdout.splitlines()
            for line in lines:
                if ('[+]' in line) and ('WPS pin' in line):
                    pin = line.split(':')[-1].strip()

                    if pin == '<empty>':
                        pin = '\'\''

                    return pin

        return False

    def _getPixieCmd(self, full_range: bool = False) -> list[str]:
        """Generates a list representing the command for the pixiewps tool."""

        pixiecmd = ['pixiewps']
        pixiecmd.extend([
            '--pke', self.PKE,
            '--pkr', self.PKR,
            '--e-hash1', self.E_HASH1,
            '--e-hash2', self.E_HASH2,
            '--authkey', self.AUTHKEY,
            '--e-nonce', self.E_NONCE,
            '--r-nonce', self.R_NONCE,
            '--e-bssid', self.BSSID
        ])

        # Enable all modes
        pixiecmd.extend(['--mode', '1,2,3,4,5'])

        if full_range:
            pixiecmd.append('--force')

        return pixiecmd

    def clear(self):
        """Resets the pixiewps variables."""
        self.__init__()
