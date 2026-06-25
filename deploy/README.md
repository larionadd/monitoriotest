# Перенесення бота на сервер

Інструкція розрахована на Ubuntu 22.04/24.04 VPS.

## 1. Підготувати архів на Windows

У папці проєкту зупиніть локального бота і зробіть копію бази:

```powershell
.\.venv\Scripts\python.exe deploy\backup_sqlite.py data\media_monitor.sqlite3 backup\media_monitor.sqlite3
```

Передавайте на сервер код проєкту без `config.json`, `.venv`, `logs/`, `reports/`.
Файл `backup\media_monitor.sqlite3` передайте окремо, якщо потрібно зберегти користувачів, ключі, підписки й історію відправок.

## 2. Встановити на сервері

### Варіант A: автоматично з Windows

Якщо на Windows доступні `ssh` і `scp`, можна завантажити архів, базу і запустити встановлення однією командою:

```powershell
.\deploy\upload_to_server.ps1 -HostName SERVER_IP -User ubuntu
```

Для нестандартного SSH-порту або ключа:

```powershell
.\deploy\upload_to_server.ps1 -HostName SERVER_IP -User ubuntu -Port 22 -IdentityFile C:\path\key.pem
```

Скрипт створить свіжий SQLite-бекап, збере архів без `config.json`, завантажить файли в `/tmp/media-monitor-bot-transfer`, встановить service, перенесе базу і створить серверний env-файл з токеном та адмінами з локального `config.json`.

Після першого встановлення можна перевірити env-файл:

```bash
sudo cat /etc/media-monitor-bot/media-monitor-bot.env
```

### Варіант B: вручну на сервері

Скопіюйте проєкт на сервер, наприклад у `/tmp/media-monitor-bot`, і запустіть:

```bash
cd /tmp/media-monitor-bot
sudo bash deploy/install_server.sh
```

Скрипт встановить код у `/opt/media-monitor-bot`, створить системного користувача `media-monitor`, venv, каталоги даних і `systemd` service.

## 3. Додати секрети

Відкрийте env-файл:

```bash
sudo nano /etc/media-monitor-bot/media-monitor-bot.env
```

Заповніть:

```bash
TELEGRAM_BOT_TOKEN=ваш_токен
ADMIN_CHAT_IDS=263677182,431044822
```

Токен не потрібно записувати в код або Git.

## 4. Перенести базу

Якщо переносите існуючих користувачів:

```bash
sudo systemctl stop media-monitor-bot
sudo cp media_monitor.sqlite3 /var/lib/media-monitor-bot/media_monitor.sqlite3
sudo chown media-monitor:media-monitor /var/lib/media-monitor-bot/media_monitor.sqlite3
sudo systemctl start media-monitor-bot
```

Якщо базу не переносити, бот створить нову порожню базу при першому запуску.

## 5. Керування ботом

```bash
sudo systemctl start media-monitor-bot
sudo systemctl stop media-monitor-bot
sudo systemctl restart media-monitor-bot
sudo systemctl status media-monitor-bot
```

Логи:

```bash
sudo journalctl -u media-monitor-bot -f
sudo tail -f /var/log/media-monitor-bot/bot.out.log
sudo tail -f /var/log/media-monitor-bot/bot.err.log
```

## 6. Оновлення коду

Завантажте нову версію проєкту на сервер і знову виконайте:

```bash
cd /tmp/media-monitor-bot
sudo bash deploy/install_server.sh
sudo systemctl restart media-monitor-bot
```

Скрипт не перезаписує `/etc/media-monitor-bot/media-monitor-bot.env`, `/etc/media-monitor-bot/config.json` і базу в `/var/lib/media-monitor-bot`.
