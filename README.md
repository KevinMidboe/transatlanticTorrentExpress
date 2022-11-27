# 🚅 Transatlantic Torrent Express
> Agent for transporting files from remote host.

## Install
Download repo:

```bash
git clone https://github.com/kevinmidboe/transatlanticTorrentExpress
cd transatlanticTorrentExpress
```

Also setup to require [delugeClient](https://github.com/KevinMidboe/delugeClient) to remove after transfered. Install the package using pip command: 
```bash
pip3 install delugeClient-kevin
```

## Configure
Create copy of config and edit following values:

```bash
cp config.ini.default config.ini
```

```ini
[SSH]
host=
user=

[FILES]
remote=
local=

[LOGGER]
CH_LEVEL=INFO

[ELASTIC]
host=
port=
ssl=
api_key=

```

## Run

```bash
python3 src/transatlanticTorrentExpress.py
```