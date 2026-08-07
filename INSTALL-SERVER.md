# Installing Marvel Champions Digital: Ronin Edition as a Server

> Version 0.6.0 — “Echo”

This guide is intended for Debian, Ubuntu, or Armbian with Python 3.10 or newer. The server is installed in `/opt/marvel-lcg` and runs under a dedicated `marvel-lcg` user.

## 1. Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip rsync
python3 --version
```

## 2. Create the service user and copy the game

Run these commands from the directory containing the game's source code:

```bash
sudo useradd --system --home-dir /opt/marvel-lcg --shell /usr/sbin/nologin marvel-lcg
sudo install -d -o marvel-lcg -g marvel-lcg /opt/marvel-lcg
sudo rsync -a --exclude='.git' --exclude='.venv' ./ /opt/marvel-lcg/
sudo chown -R marvel-lcg:marvel-lcg /opt/marvel-lcg
```

If the `marvel-lcg` user already exists, you can ignore the error reported by `useradd`.

## 3. Create the Python virtual environment

```bash
sudo -u marvel-lcg python3 -m venv /opt/marvel-lcg/.venv
sudo -u marvel-lcg /opt/marvel-lcg/.venv/bin/pip install --upgrade pip
sudo -u marvel-lcg /opt/marvel-lcg/.venv/bin/pip install -r /opt/marvel-lcg/requirements.txt
```

The server address in `launch.json` must be set to `0.0.0.0:2345` so that other devices on the local network can connect to it.

## 4. Install the systemd unit

```bash
sudo install -m 0644 /opt/marvel-lcg/marvel-lcg.service /etc/systemd/system/marvel-lcg.service
sudo systemctl daemon-reload
sudo systemctl enable --now marvel-lcg.service
```

Check the service status and follow its log with:

```bash
sudo systemctl status marvel-lcg.service
sudo journalctl -u marvel-lcg.service -f
```

After starting the service, open `http://SERVER_IP_ADDRESS:2345` on your phone or another device. Run `hostname -I` on the server to find its IP address. If a firewall is enabled, allow TCP port `2345` only for the local network.

## Updating

Copy the files again with `rsync`, install any updated dependencies, and restart the service:

```bash
sudo rsync -a --exclude='.git' --exclude='.venv' ./ /opt/marvel-lcg/
sudo chown -R marvel-lcg:marvel-lcg /opt/marvel-lcg
sudo -u marvel-lcg /opt/marvel-lcg/.venv/bin/pip install -r /opt/marvel-lcg/requirements.txt
sudo systemctl restart marvel-lcg.service
```
