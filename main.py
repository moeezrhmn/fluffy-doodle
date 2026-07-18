# Entry point of the app
from contextlib import asynccontextmanager
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import user_router, tools_router
from app.services.tools.media import compress_service, audio_service, trim_service

from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from app.config import settings
from asyncio import timeout
import asyncio
import os
import json as _json
from app import config
from app.utils import monitor
from app.utils import concurrency


REQUEST_TIMEOUT = int(settings.REQUEST_TIMEOUT)

MAX_QUEUE_THRESHOLD = 10  # reject new tool requests when queue exceeds this

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/tools/") and concurrency.downloads_queued >= MAX_QUEUE_THRESHOLD:
            return JSONResponse(
                status_code=429,
                content={"detail": "Server is busy. Please try again in a moment.", "queued": concurrency.downloads_queued}
            )

        region = request.query_params.get("region")
        video_url = None
        data = None
        if request.method in ("POST", "PUT", "PATCH"):
            try:
                body = await request.body()
                data = _json.loads(body)
                region = region or data.get("region")
                video_url = data.get("url")
            except Exception:
                pass
        track = request.url.path.startswith(("/tools/", "/users/"))
        entry = None
        if track:
            client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (request.client.host if request.client else "-")
            print(f"[request] {request.method} {request.url.path} | region={region or '-'} | url={video_url or '-'} | ip={client_ip}")
            entry = monitor.request_started(request.url.path, request.method, region, video_url, req_id=id(request), payload=data, ip=client_ip)
        try:
            response = await call_next(request)
            if track:
                error_body = None
                if response.status_code >= 400:
                    chunks = []
                    async for chunk in response.body_iterator:
                        chunks.append(chunk)
                    raw = b"".join(chunks)
                    error_body = raw.decode("utf-8", errors="ignore")[:1000]
                    response = Response(
                        content=raw,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                monitor.request_finished(entry, response.status_code, error_body)
            return response
        except Exception as exc:
            if track and entry:
                monitor.request_finished(entry, 500)
            raise


class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            async with timeout(REQUEST_TIMEOUT):
                response = await call_next(request)
                return response
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={
                    "error": "Request timeout",
                    "message": f"Request took longer than {REQUEST_TIMEOUT} seconds to process",
                    "timeout": REQUEST_TIMEOUT
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": str(e)
                }
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    compress_service.start_workers()
    audio_service.start_workers()
    trim_service.start_workers()
    try:
        config.redis_client.ping()
        config.redis_client.set("monitor:active", 0)
        print("[startup] Redis connected ✓")
    except Exception as e:
        raise RuntimeError(f"[startup] Redis unavailable — cannot start.")
    yield


app = FastAPI(lifespan=lifespan)

# Add timeout middleware
app.add_middleware(TimeoutMiddleware)
app.add_middleware(RequestLogMiddleware)

# Mount downloads directory for static file serving
if not os.path.exists(config.DOWNLOAD_DIR):
    os.makedirs(config.DOWNLOAD_DIR)
app.mount("/downloads", StaticFiles(directory=config.DOWNLOAD_DIR), name="downloads")

app.include_router(user_router.router)
app.include_router(tools_router.router)


# Root path
@app.get('/')
async def root():
    return {'message':'Tools APIs developed by MOEEZ UR REHMAN - [Portfolio: moeezrehman.quanter.dev] '}


@app.websocket("/ws/monitor")
async def ws_monitor(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            snapshot = monitor.get_snapshot(
                concurrency.downloads_active,
                concurrency.downloads_queued,
            )
            await websocket.send_text(_json.dumps(snapshot))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.get("/monitor", response_class=HTMLResponse)
async def monitor_dashboard():
    return HTMLResponse(content=MONITOR_HTML)


MONITOR_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>API Monitor</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #0f1117; color: #e2e8f0; font-family: 'Segoe UI', system-ui, sans-serif; font-size: 14px; }
  header { background: #1a1d27; border-bottom: 1px solid #2d3148; padding: 14px 24px; display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 18px; font-weight: 600; color: #a78bfa; }
  #status { font-size: 12px; padding: 3px 10px; border-radius: 20px; background: #1e3a2f; color: #4ade80; border: 1px solid #16a34a; }
  #status.disconnected { background: #3b1f1f; color: #f87171; border-color: #dc2626; }
  #uptime { margin-left: auto; color: #94a3b8; font-size: 12px; }
  main { padding: 20px 24px; max-width: 1400px; margin: 0 auto; }

  .grid { display: grid; gap: 16px; margin-bottom: 20px; }
  .grid-4 { grid-template-columns: repeat(4, 1fr); }
  .grid-2 { grid-template-columns: repeat(2, 1fr); }

  .card { background: #1a1d27; border: 1px solid #2d3148; border-radius: 10px; padding: 18px; }
  .card h2 { font-size: 11px; text-transform: uppercase; letter-spacing: .08em; color: #64748b; margin-bottom: 8px; }
  .card .val { font-size: 32px; font-weight: 700; color: #e2e8f0; }
  .card .val.green { color: #4ade80; }
  .card .val.red { color: #f87171; }
  .card .val.yellow { color: #fbbf24; }
  .card .val.purple { color: #a78bfa; }

  .dl-bar { display: flex; align-items: center; gap: 10px; margin-top: 6px; }
  .bar-wrap { flex: 1; height: 8px; background: #2d3148; border-radius: 4px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 4px; background: #a78bfa; transition: width .4s ease; }
  .bar-fill.warn { background: #fbbf24; }
  .dl-label { font-size: 12px; color: #94a3b8; min-width: 90px; }

  table { width: 100%; border-collapse: collapse; }
  thead th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #64748b; padding: 6px 10px; border-bottom: 1px solid #2d3148; }
  tbody tr { border-bottom: 1px solid #1e2235; }
  tbody tr:hover { background: #20243a; }
  td { padding: 7px 10px; font-size: 13px; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
  .badge.ok { background: #1e3a2f; color: #4ade80; }
  .badge.err { background: #3b1f1f; color: #f87171; }
  .badge.method { background: #1e2a48; color: #60a5fa; }
  .mono { font-family: monospace; font-size: 12px; color: #94a3b8; }
  .truncate { max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
</head>
<body>
<header>
  <h1>&#9679; API Monitor</h1>
  <span id="status">Connecting…</span>
  <span id="uptime"></span>
</header>
<main>
  <div class="grid grid-4">
    <div class="card"><h2>Active Requests</h2><div class="val purple" id="active">—</div></div>
    <div class="card"><h2>Total Requests</h2><div class="val" id="total">—</div></div>
    <div class="card"><h2>Successful</h2><div class="val green" id="success">—</div></div>
    <div class="card"><h2>Failed</h2><div class="val red" id="failed">—</div></div>
  </div>

  <div class="grid grid-2" style="margin-bottom:20px;">
    <div class="card">
      <h2>Download Slots</h2>
      <div class="dl-bar" style="margin-top:10px;">
        <span class="dl-label">Active (<span id="dl-active">0</span>/<span id="dl-max">3</span>)</span>
        <div class="bar-wrap"><div class="bar-fill" id="dl-active-bar" style="width:0%"></div></div>
      </div>
      <div class="dl-bar" style="margin-top:8px;">
        <span class="dl-label">Queued (<span id="dl-queued">0</span>)</span>
        <div class="bar-wrap"><div class="bar-fill warn" id="dl-queued-bar" style="width:0%"></div></div>
      </div>
    </div>
    <div class="card">
      <h2>Success Rate</h2>
      <div class="val green" id="rate">—</div>
      <div class="dl-bar" style="margin-top:10px;">
        <div class="bar-wrap" style="height:10px;"><div class="bar-fill" id="rate-bar" style="width:0%;background:#4ade80;"></div></div>
      </div>
    </div>
  </div>

  <div class="grid grid-2">
    <div class="card">
      <h2>Top Endpoints</h2>
      <table>
        <thead><tr><th>Path</th><th>Requests</th><th>Failed</th></tr></thead>
        <tbody id="paths-body"><tr><td colspan="3" style="color:#64748b;text-align:center;padding:20px;">Waiting for data…</td></tr></tbody>
      </table>
    </div>
    <div class="card">
      <h2>Recent Requests</h2>
      <table>
        <thead><tr><th>Method</th><th>Path</th><th>Status</th><th>Time</th><th>Region</th><th>IP</th><th>Proxy</th></tr></thead>
        <tbody id="recent-body"><tr><td colspan="7" style="color:#64748b;text-align:center;padding:20px;">Waiting for data…</td></tr></tbody>
      </table>
    </div>
  </div>

  <div class="card" style="margin-top:16px;">
    <h2>Failed Requests <span id="failed-count" style="color:#f87171;margin-left:6px;"></span></h2>
    <div id="failed-list" style="margin-top:10px;display:flex;flex-direction:column;gap:10px;">
      <p style="color:#64748b;text-align:center;padding:20px;">No failures recorded.</p>
    </div>
  </div>
</main>

<script>
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(proto + '://' + location.host + '/ws/monitor');
  const statusEl = document.getElementById('status');

  // Previous serialized snapshots for change detection
  let _prevPaths = '', _prevRecent = '', _prevFailed = '', _prevFailedCount = -1;

  ws.onopen = () => { statusEl.textContent = 'Live'; statusEl.className = ''; };
  ws.onclose = () => { statusEl.textContent = 'Disconnected'; statusEl.className = 'disconnected'; setTimeout(() => location.reload(), 3000); };

  ws.onmessage = e => {
    const d = JSON.parse(e.data);

    // Stat numbers — textContent only, never interrupts selection
    document.getElementById('uptime').textContent = 'Up ' + d.uptime;
    document.getElementById('active').textContent = d.active_requests;
    document.getElementById('total').textContent = d.total_requests;
    document.getElementById('success').textContent = d.success_requests;
    document.getElementById('failed').textContent = d.failed_requests;

    const dlMax = d.downloads.max || 3;
    document.getElementById('dl-active').textContent = d.downloads.active;
    document.getElementById('dl-max').textContent = dlMax;
    document.getElementById('dl-queued').textContent = d.downloads.queued;
    document.getElementById('dl-active-bar').style.width = Math.min(100, (d.downloads.active / dlMax) * 100) + '%';
    document.getElementById('dl-queued-bar').style.width = Math.min(100, (d.downloads.queued / dlMax) * 100) + '%';

    const total = d.total_requests || 0;
    const rate = total ? Math.round((d.success_requests / total) * 100) : 100;
    document.getElementById('rate').textContent = rate + '%';
    document.getElementById('rate-bar').style.width = rate + '%';

    // Top endpoints — rebuild only if data changed
    const pathsSig = JSON.stringify(d.top_paths);
    if (pathsSig !== _prevPaths) {
      _prevPaths = pathsSig;
      const pathsBody = document.getElementById('paths-body');
      if (d.top_paths.length) {
        pathsBody.innerHTML = d.top_paths.map(p =>
          '<tr><td class="mono truncate">' + esc(p.path) + '</td><td>' + p.total + '</td><td class="' + (p.failed ? 'red' : '') + '">' + p.failed + '</td></tr>'
        ).join('');
      }
    }

    // Recent requests — rebuild only if first item changed (new request came in)
    const recentSig = JSON.stringify(d.recent.slice(0, 3));
    if (recentSig !== _prevRecent) {
      _prevRecent = recentSig;
      const recentBody = document.getElementById('recent-body');
      if (d.recent.length) {
        recentBody.innerHTML = d.recent.map(r => {
          const ok = r.status && r.status < 400;
          return '<tr>' +
            '<td><span class="badge method">' + esc(r.method) + '</span></td>' +
            '<td class="mono truncate" style="max-width:180px">' + esc(r.path) + '</td>' +
            '<td><span class="badge ' + (ok ? 'ok' : 'err') + '">' + (r.status || '…') + '</span></td>' +
            '<td class="mono">' + (r.duration_ms != null ? (r.duration_ms >= 1000 ? (r.duration_ms/1000).toFixed(1)+'s' : r.duration_ms+'ms') : '…') + '</td>' +
            '<td class="mono">' + esc(r.region || '-') + '</td>' +
            '<td class="mono" style="color:#94a3b8;">' + esc(r.ip || '-') + '</td>' +
            '<td class="mono" style="color:#a78bfa;">' + (r.proxy_kb ? (r.proxy_kb >= 1024 ? (r.proxy_kb/1024).toFixed(1)+'MB' : r.proxy_kb+'KB') : '-') + '</td>' +
            '</tr>';
        }).join('');
      }
    }

    // Failed list — only rebuild when count changes (preserves open <details> and selected text)
    const failedCount = d.failed_list ? d.failed_list.length : 0;
    document.getElementById('failed-count').textContent = failedCount ? '(' + failedCount + ')' : '';
    if (failedCount !== _prevFailedCount) {
      _prevFailedCount = failedCount;
      const failedList = document.getElementById('failed-list');
      if (failedCount) {
        failedList.innerHTML = d.failed_list.map(f => {
          const ts = f.started_at ? new Date(f.started_at * 1000).toLocaleTimeString() : '-';
          const payload = f.payload ? JSON.stringify(f.payload, null, 2) : null;
          const error = f.error || null;
          return '<div style="background:#1e2235;border:1px solid #3b1f1f;border-radius:8px;padding:14px;">' +
            '<div style="display:flex;gap:10px;align-items:center;margin-bottom:8px;">' +
              '<span class="badge method">' + esc(f.method) + '</span>' +
              '<span class="mono" style="color:#e2e8f0;">' + esc(f.path) + '</span>' +
              '<span class="badge err">' + esc(f.status) + '</span>' +
              '<span class="mono" style="color:#64748b;margin-left:auto;">' + ts + ' &bull; ' + esc(f.region || '-') + ' &bull; ' + esc(f.ip || '-') + (f.proxy_kb ? ' &bull; <span style=\"color:#a78bfa;\">' + (f.proxy_kb >= 1024 ? (f.proxy_kb/1024).toFixed(1)+'MB' : f.proxy_kb+'KB') + '</span>' : '') + ' &bull; ' + (f.duration_ms != null ? (f.duration_ms >= 1000 ? (f.duration_ms/1000).toFixed(1)+'s' : f.duration_ms+'ms') : '') + '</span>' +
            '</div>' +
            (f.url && f.url !== '-' ? '<div style="font-size:12px;color:#94a3b8;margin-bottom:6px;">URL: <span class="mono">' + esc(f.url) + '</span></div>' : '') +
            (payload ? '<details style="margin-bottom:6px;"><summary style="cursor:pointer;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;">Payload</summary><pre style="margin-top:6px;background:#0f1117;border-radius:6px;padding:10px;font-size:11px;overflow-x:auto;color:#a78bfa;">' + esc(payload) + '</pre></details>' : '') +
            (error ? '<details open><summary style="cursor:pointer;font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:.06em;">Error</summary><pre style="margin-top:6px;background:#0f1117;border-radius:6px;padding:10px;font-size:11px;overflow-x:auto;color:#f87171;">' + esc(error) + '</pre></details>' : '') +
            '</div>';
        }).join('');
      } else {
        failedList.innerHTML = '<p style="color:#64748b;text-align:center;padding:20px;">No failures recorded.</p>';
      }
    }
  };

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }
</script>
</body>
</html>"""
