# Overview
**OneShot-Extended** performs the [Pixie Dust attack](https://forums.kali.org/showthread.php?24286-WPS-Pixie-Dust-Attack-Offline-WPS-Attack) without the requirement of monitor mode.

This is an improved version of the original OneShot

## Advantages over original OneShot
 - Highlighting of a vulnerable WPS version (1.0) in the scanner
 - Ability to save the AP right into the Network Manager of your system
 - Ability to clear the screen every scan
 - Improved Android support
 - Works on modern python versions

# Features
 - [Pixie Dust attack](https://forums.kali.org/showthread.php?24286-WPS-Pixie-Dust-Attack-Offline-WPS-Attack)
 - Offline WPS PIN generating algorithm
 - [Online WPS bruteforce](https://sviehb.files.wordpress.com/2011/12/viehboeck_wps.pdf)
 - Wi-Fi scanner with highlighting based on iw;
 - Ability to write to a file/save to network manager

# Requirements
 - Python 3.8 and above
 - [WPA Supplicant](https://www.w1.fi/wpa_supplicant/)
 - [Pixiewps](https://github.com/wiire-a/pixiewps)
 - [iw](https://wireless.wiki.kernel.org/en/users/documentation/iw)

# Usage
```
Required arguments: 
  -i, --interface INTERFACE    : Name of the interface to use

Optional arguments:
  -b, --bssid BSSID            : BSSID of the target AP
  -p, --pin PIN                : Use the specified pin (arbitrary string or 4/8 digit pin)
  -K, --pixie-dust             : Run Pixie Dust attack
  -F, --pixie-force            : Run Pixiewps with --force option (bruteforce full range)
  -B, --bruteforce             : Run online bruteforce attack
  --pbc, --push-button-connect : Run WPS push button connection

Advanced arguments:
  -d, --delay <n>              : Set the delay between pin attempts
  --vuln-list VULN_LIST        : Use custom file with vulnerable devices list

  -X, --show-pixie-cmd         : Always print Pixiewps command
  -w, --write                  : Write credentials to the file on success
  -s, --save                   : Save the AP to network manager on success
  -l, --loop                   : Run in a loop
  -c, --clear                  : Clear the screen on every wi-fi scan
  -r, --reverse-scan           : Reverse order of networks in the list of networks. Useful on small displays
  --mtk-wifi                   : Activate MediaTek Wi-Fi interface driver on startup and deactivate it on exit (for internal Wi-Fi adapters implemented in MediaTek SoCs). 
                               : Turn off Wi-Fi in the system settings before using this.
  --iface-down                 : Down network interface when the work is finished
  -v, --verbose                : Verbose output
  -h, --help                   : show this help message and exit
 ```

# Installation
## Termux
**Please note that root access is required.**  

**Installing requirements**
 ```shell
 pkg install -y root-repo
 pkg install -y git tsu python wpa-supplicant pixiewps iw openssl
 ```
**Getting OneShot-Extended**
 ```shell
 cd ~
 git clone --depth 1 https://github.com/chickendrop89/OneShot-Extended ose
 ```
**Running**
 ```shell
 sudo python ose/ose.py -i wlan0
 ```

## Linux distributions 
**Install these packages through your distro's package manager:**
 ```shell
 python3 wpa-supplicant iw wget pixiewps
 ```
 
**Getting OneShot**
 ```shell
 cd ~
 git clone --depth 1 https://github.com/chickendrop89/OneShot-Extended ose
 ```
**Running**
 ```shell
 sudo python ose/ose.py -i wlan0
 ```

-----

## Usage examples
Start Pixie Dust attack on a specified BSSID:
 ```shell
 sudo python3 ose.py -i wlan0 -b 00:90:4C:C1:AC:21 -K
 ```
Show avaliable networks and start Pixie Dust attack on a specified network:
 ```shell
 sudo python3 ose.py -i wlan0 -K
 ```
Launch online WPS bruteforce with the specified first half of the PIN:
 ```shell
 sudo python3 ose.py -i wlan0 -b 00:90:4C:C1:AC:21 -B -p 1234
 ```
 Start WPS push button connection:s
 ```shell
 sudo python3 ose.py -i wlan0 --pbc
 ```

-----

## Troubleshooting
**"RTNETLINK answers: Operation not possible due to RF-kill"**
 Just run:
- ```sudo rfkill unblock wifi```

**"Device or resource busy (-16)"**
- Try disabling Wi-Fi in the system settings and kill the Network manager. Alternatively, you can try running OneShot-Extended with ```--iface-down``` argument.

**The wlan0 interface disappears when Wi-Fi is disabled on Android devices with MediaTek SoC**
- Try running Oneshot-Extended with the `--mtk-wifi` flag to initialize Wi-Fi device driver.

-----

# Acknowledgements
## Special Thanks
* `kimocoder, drygdryg, chickendrop89` for extended implementation 
* `rofl0r` for initial implementation;
* `Monohrom` for testing, help in catching bugs, some ideas;
* `Wiire` for developing Pixiewps.

-----

> [!WARNING] 
> This tool is intended for educational and authorized penetration testing purposes only.
> It is not designed for, and must not be used for, illegal activities such as hacking, unauthorized access, or causing damage to systems or networks.
> By using this tool, you agree to use it responsibly and ethically, and to comply with all applicable laws and regulations.
> The developer assumes no responsibility for any misuse of this tool.

