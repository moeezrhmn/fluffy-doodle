# bgutil-ytdlp-pot-provider Server Setup

Generates YouTube PO Tokens (proof-of-origin) to bypass bot detection. Runs as an HTTP server on port 4416. yt-dlp automatically uses it via the installed plugin.

## Requirements

- Node.js >= 20 **or** Deno >= 2.0.0
- The `bgutil-ytdlp-pot-provider` directory (already in this repo)
- Python packages — covered by `pip install -r requirements.txt` (includes `yt-dlp`, `yt-dlp-ejs`, `bgutil-ytdlp-pot-provider`)

---

## 1. Install server dependencies


```bash
git clone https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git

cd bgutil-ytdlp-pot-provider/server

# Option A — Node.js (recommended for servers)
npm ci
npx tsc

# Option B — Deno
deno install --allow-scripts=npm:canvas --frozen
```

---

## 2. Run the server

**Node.js** — must compile TypeScript first, then run the compiled JS:
```bash
cd bgutil-ytdlp-pot-provider/server
npm ci
npx tsc
node build/main.js
```

> Do NOT run `node src/main.ts` directly — Node cannot run TypeScript source files.

**Deno** — runs TypeScript natively, no compile step needed:
```bash
cd bgutil-ytdlp-pot-provider/server/node_modules
deno run --allow-env --allow-net --allow-ffi=. --allow-read=. ../src/main.ts
```

Server starts on `http://127.0.0.1:4416`. Verify with:
```bash
curl http://127.0.0.1:4416/ping
```

---

## 3. Run as a systemd service (production)

Create `/etc/systemd/system/bgutil-pot.service`:

```ini
[Unit]
Description=bgutil PO Token Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/path/to/project/bgutil-ytdlp-pot-provider/server
ExecStart=node build/main.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable bgutil-pot
sudo systemctl start bgutil-pot
sudo systemctl status bgutil-pot
```

---

## How it works

- First request: fetches BotGuard JS from Google, generates an **IntegrityToken** (valid 12 hours)
- Subsequent requests: mints POTs locally from the cached token — no network calls
- Result: ~2 calls to Google per day regardless of traffic volume
- Tokens are also cached per video for 6 hours (`TOKEN_TTL` env var to change)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `curl /ping` fails | Server not running, check `systemctl status bgutil-pot` |
| yt-dlp not using bgutil | Run `yt-dlp -v URL` and check for `bgutil:http` in PO Token Providers line |
| Plugin not found | `pip install bgutil-ytdlp-pot-provider` inside the venv |
| Port conflict | Pass `--port 4417` to the server and update `base_url` in `youtube_service.py` |