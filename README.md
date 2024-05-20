# WireGuard GUI

Welcome to the VPN Setup GUI project. This is a Free and Open Source Software (FOSS) project aimed at helping small VPN operators set up their networks quickly and easily.

## Project Overview

Setting up a VPN can be a complex task, especially for small operators who may not have a dedicated IT team. This project aims to simplify that process by providing a graphical user interface (GUI) for setting up VPN networks.

With this tool, operators can configure their VPN networks without needing to understand complex networking concepts or write configuration files by hand. The GUI provides a simple, intuitive interface that guides operators through the setup process step by step.

We welcome contributions from the community. If you're interested in contributing, please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for more information.

At present, the development roadmap is here [ROADMAP.md](ROADMAP.md)

## Installation

At present, simply clone this repository onto a Linux machine. A Debian-based linux build is the only currently supported OS.

```bash
git clone https://github.com/radawson/wireguard-gui
```

After the repository is cloned, change directory into the wireguard-gui directory

```bash
cd wireguard-gui
```

Next, install the python requirements with sudo to make them global. Yes, you will get a warning about this.

```bash
sudo pip install -r requirements.txt
```

Once the installation is complete, change directory into src.

```bash
cd src
```

Next, Make any adjustments you need to make to config.yaml. Note that the default IP address is localhost, 127.0.0.1. If you want to access the web interface remotely, change this to an appropriate IP address.

***Security warning*** You can also use 0.0.0.0 to listen on all IP addresses, but understand the implications of this.

The one key in config.yaml you MUST change is the SUDO_PASSWORD. This must be the sudo password for the user that will be running the python script. We DO NOT recommend running the entire python web server with sudo. Your user that runs the wepython script will have to have sudo permission to set up the WireGuard services. If you are only using the datbase for tracking, you won't have tyo use sudo or a sudo user because you won't be elevating permissions.

```bash
SUDO_PASSWORD: 'changeme'
```

The MODE key in the config file determines whether this server will run as a wireguard server (hub) or as a database for configuration files. The options for this key are 'server' or 'database'

This is also a good time to make sure that your firewall has port 5000 (default) open for the webserver. You will also need to open port 51820 UDP (default) for the WireGuard service.

Examples using ufw:

```bash
sudo ufw allow 5000/tcp
sudo ufw allow 51820/udp
```

## WireGuard-tools

Pure Python reimplementation of wireguard-tools with an aim to provide easily
reusable library functions to handle reading and writing of
[WireGuard®](https://www.wireguard.com/) configuration files as well as
interacting with WireGuard devices, both in-kernel through the Netlink API and
userspace implementations through the cross-platform UAPI API.

### Installation/Usage

```sh
    pipx install wireguard-tools
    wg-py --help
```

Implemented `wg` command line functionality,

- [x] show - Show configuration and device information
- [x] showconf - Dump current device configuration
- [ ] set - Change current configuration, add/remove/change peers
- [x] setconf - Apply configuration to device
- [ ] addconf - Append configuration to device
- [x] syncconf - Synchronizes configuration with device
- [x] genkey, genpsk, pubkey - Key generation

Also includes some `wg-quick` functions,

- [ ] up, down - Create and configure WireGuard device and interface
- [ ] save - Dump device and interface configuration
- [x] strip - Filter wg-quick settings from configuration

Needs root (sudo) access to query and configure the WireGuard devices through
netlink. But root doesn't know about the currently active virtualenv, you may
have to pass the full path to the script in the virtualenv, or use
`python3 -m wireguard_tools`

```sh
    sudo `which wg-py` showconf <interface>
    sudo /path/to/venv/python3 -m wireguard_tools showconf <interface>
```

### Library usage

#### Parsing WireGuard keys

The WireguardKey class will parse base64-encoded keys, the default base64
encoded string, but also an urlsafe base64 encoded variant. It also exposes
both private key generating and public key deriving functions. Be sure to pass
any base64 or hex encoded keys as 'str' and not 'bytes', otherwise it will
assume the key was already decoded to its raw form.

```python
from wireguard_tools import WireguardKey

private_key = WireguardKey.generate()
public_key = private_key.public_key()

# print base64 encoded key
print(public_key)

# print urlsafe encoded key
print(public_key.urlsafe)

# print hexadecimal encoded key
print(public_key.hex())
```

#### Working with WireGuard configuration files

The WireGuard configuration file is similar to, but not quite, the INI format
because it has duplicate keys for both section names (i.e. [Peer]) as well as
configuration keys within a section. According to the format description,
AllowedIPs, Address, and DNS configuration keys 'may be specified multiple
times'.

```python
from wireguard_tools import WireguardConfig

with open("wg0.conf") as fh:
    config = WireguardConfig.from_wgconfig(fh)
```

Also supported are the "Friendly Tags" comments as introduced by
prometheus-wireguard-exporter, where a `[Peer]` section can contain
comments which add a user friendly description and/or additional attributes.

```config
[Peer]
# friendly_name = Peer description for end users
# friendly_json = {"flat"="json", "dictionary"=1, "attribute"=2}
...
```

These will show up as additional `friendly_name` and `friendly_json` attributes
on the WireguardPeer object.

We can also serialize and deserialize from a simple dict-based format which
uses only basic JSON datatypes and, as such, can be used to convert to various
formats (i.e. json, yaml, toml, pickle) either to disk or to pass over a
network.

```python
from wireguard_tools import WireguardConfig
from pprint import pprint

dict_config = dict(
    private_key="...",
    peers=[
        dict(
            public_key="...",
            preshared_key=None,
            endpoint_host="remote_host",
            endpoint_port=5120,
            persistent_keepalive=30,
            allowed_ips=["0.0.0.0/0"],
            friendly_name="Awesome Peer",
        ),
    ],
)
config = WireguardConfig.from_dict(dict_config)

dict_config = config.asdict()
pprint(dict_config)
```

Finally, there is a `to_qrcode` function that returns a segno.QRCode object
which contains the configuration. This can be printed and scanned with the
wireguard-android application. Careful with these because the QRcode exposes
an easily captured copy of the private key as part of the configuration file.
It is convenient, but definitely not secure.

```python
from wireguard_tools import WireguardConfig
from pprint import pprint

dict_config = dict(
    private_key="...",
    peers=[
        dict(
            public_key="...",
            preshared_key=None,
            endpoint_host="remote_host",
            endpoint_port=5120,
            persistent_keepalive=30,
            allowed_ips=["0.0.0.0/0"],
        ),
    ],
)
config = WireguardConfig.from_dict(dict_config)

qr = config.to_qrcode()
qr.save("wgconfig.png")
qr.terminal(compact=True)
```

#### Working with WireGuard devices

```python
from wireguard_tools import WireguardDevice

ifnames = [device.interface for device in WireguardDevice.list()]

device = WireguardDevice.get("wg0")

wgconfig = device.get_config()

device.set_config(wgconfig)
```

### Bugs

The setconf/syncconf implementation is not quite correct. They currently use
the same underlying set of operations but netlink-api's `set_config`
implementation actually does something closer to syncconf, while the uapi-api
implementation matches setconf.

This implementation has only been tested on Linux where we've only actively
used a subset of the available functionality, i.e. the common scenario is
configuring an interface only once with just a single peer.

### Licenses

wireguard-tools is MIT licensed

Copyright (c) 2022-2024 Carnegie Mellon University

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

`wireguard_tools/curve25519.py` was released in the public domain

Copyright Nicko van Someren, 2021. This code is released into the public domain.
<https://gist.github.com/nickovs/cc3c22d15f239a2640c185035c06f8a3>

"WireGuard" is a registered trademark of Jason A. Donenfeld.
