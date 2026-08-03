# Встановлення Marvel LCG як сервера

Інструкція розрахована на Debian, Ubuntu або Armbian із Python 3.10 чи новішим. Сервер встановлюється в `/opt/marvel-lcg` і працює від окремого користувача `marvel-lcg`.

## 1. Встановлення системних пакетів

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip rsync
python3 --version
```

## 2. Створення користувача і копіювання гри

Виконайте з каталогу з вихідним кодом гри:

```bash
sudo useradd --system --home-dir /opt/marvel-lcg --shell /usr/sbin/nologin marvel-lcg
sudo install -d -o marvel-lcg -g marvel-lcg /opt/marvel-lcg
sudo rsync -a --exclude='.git' --exclude='.venv' ./ /opt/marvel-lcg/
sudo chown -R marvel-lcg:marvel-lcg /opt/marvel-lcg
```

Якщо користувач `marvel-lcg` уже існує, помилку від `useradd` можна пропустити.

## 3. Створення Python-оточення

```bash
sudo -u marvel-lcg python3 -m venv /opt/marvel-lcg/.venv
sudo -u marvel-lcg /opt/marvel-lcg/.venv/bin/pip install --upgrade pip
sudo -u marvel-lcg /opt/marvel-lcg/.venv/bin/pip install -r /opt/marvel-lcg/requirements.txt
```

У `launch.json` адреса сервера має бути `0.0.0.0:2345`, щоб до нього можна було підключитися з іншого пристрою в локальній мережі.

## 4. Встановлення systemd unit

```bash
sudo install -m 0644 /opt/marvel-lcg/marvel-lcg.service /etc/systemd/system/marvel-lcg.service
sudo systemctl daemon-reload
sudo systemctl enable --now marvel-lcg.service
```

Перевірка стану і перегляд журналу:

```bash
sudo systemctl status marvel-lcg.service
sudo journalctl -u marvel-lcg.service -f
```

Після запуску відкрийте на телефоні `http://IP_АДРЕСА_СЕРВЕРА:2345`. IP-адресу можна подивитися командою `hostname -I`. Якщо використовується firewall, дозвольте TCP-порт `2345` лише для локальної мережі.

## Оновлення

Знову скопіюйте файли через `rsync`, встановіть залежності та перезапустіть службу:

```bash
sudo rsync -a --exclude='.git' --exclude='.venv' ./ /opt/marvel-lcg/
sudo chown -R marvel-lcg:marvel-lcg /opt/marvel-lcg
sudo -u marvel-lcg /opt/marvel-lcg/.venv/bin/pip install -r /opt/marvel-lcg/requirements.txt
sudo systemctl restart marvel-lcg.service
```
