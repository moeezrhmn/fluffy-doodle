import time
import json
from contextvars import ContextVar
from app.config import redis_client as _r

# Middleware sets _req_id in parent task → child task inherits it (read-only inheritance works).
# Services write bytes to global dict using the inherited req_id.
# Middleware reads dict directly — no back-propagation needed.
_req_id_var: ContextVar[int] = ContextVar("req_id", default=0)
_req_proxy_bytes: dict[int, int] = {}


def _set_request_id(req_id: int):
    _req_id_var.set(req_id)
    _req_proxy_bytes[req_id] = 0


def add_request_proxy_bytes(byte_count: int):
    req_id = _req_id_var.get()
    if req_id:
        _req_proxy_bytes[req_id] = _req_proxy_bytes.get(req_id, 0) + byte_count


def _get_and_reset_proxy_bytes(req_id: int) -> int:
    return _req_proxy_bytes.pop(req_id, 0)

STATS_KEY = "monitor:stats"
RECENT_KEY = "monitor:recent"
FAILED_KEY = "monitor:failed"
ACTIVE_KEY = "monitor:active"
PATH_PREFIX = "monitor:path:"

RECENT_MAX = 100
FAILED_MAX = 50


def request_started(path: str, method: str, region: str, video_url: str, req_id: int, payload: dict = None, ip: str = None) -> dict:
    try:
        _r.incr(ACTIVE_KEY)
        _r.hincrby(STATS_KEY, "total", 1)
        _r.hsetnx(STATS_KEY, "start_time", time.time())
    except Exception as e:
        print(f"[monitor] Redis error: {e}")
    _set_request_id(req_id)
    return {
        "path": path,
        "method": method,
        "region": region or "-",
        "url": video_url or "-",
        "payload": payload,
        "ip": ip or "-",
        "req_id": req_id,
        "started_at": time.time(),
    }


def request_finished(entry: dict, status_code: int, error_body: str = None):
    try:
        if int(_r.get(ACTIVE_KEY) or 0) > 0:
            _r.decr(ACTIVE_KEY)

        if status_code < 400:
            _r.hincrby(STATS_KEY, "success", 1)
        else:
            _r.hincrby(STATS_KEY, "failed", 1)

        duration_ms = round((time.time() - entry["started_at"]) * 1000)
        path_key = PATH_PREFIX + entry["path"]
        _r.hincrby(path_key, "total", 1)
        if status_code >= 400:
            _r.hincrby(path_key, "failed", 1)

        proxy_bytes = _get_and_reset_proxy_bytes(entry.get("req_id", 0))
        record = {
            "path": entry["path"],
            "method": entry["method"],
            "region": entry["region"],
            "url": entry["url"],
            "ip": entry.get("ip", "-"),
            "status": status_code,
            "duration_ms": duration_ms,
            "started_at": entry["started_at"],
            "proxy_kb": round(proxy_bytes / 1024, 1) if proxy_bytes else 0,
        }
        _r.lpush(RECENT_KEY, json.dumps(record))
        _r.ltrim(RECENT_KEY, 0, RECENT_MAX - 1)

        if status_code >= 400:
            failed_record = {**record, "payload": entry.get("payload"), "error": error_body}
            _r.lpush(FAILED_KEY, json.dumps(failed_record))
            _r.ltrim(FAILED_KEY, 0, FAILED_MAX - 1)

    except Exception as e:
        print(f"[monitor] Redis error in request_finished: {e}")


def get_snapshot(downloads_active: int, downloads_queued: int) -> dict:
    try:
        stats = _r.hgetall(STATS_KEY)
        total = int(stats.get(b"total", 0))
        success = int(stats.get(b"success", 0))
        failed_count = int(stats.get(b"failed", 0))
        start_time = float(stats.get(b"start_time", time.time()))
        active = int(_r.get(ACTIVE_KEY) or 0)

        uptime = int(time.time() - start_time)
        hours, rem = divmod(uptime, 3600)
        minutes, seconds = divmod(rem, 60)

        path_keys = _r.keys(PATH_PREFIX + "*")
        top_paths = []
        for pk in path_keys:
            ph = _r.hgetall(pk)
            top_paths.append({
                "path": pk.decode().replace(PATH_PREFIX, ""),
                "total": int(ph.get(b"total", 0)),
                "failed": int(ph.get(b"failed", 0)),
            })
        top_paths.sort(key=lambda x: x["total"], reverse=True)

        recent = [json.loads(x) for x in _r.lrange(RECENT_KEY, 0, 29)]
        failed_list = [json.loads(x) for x in _r.lrange(FAILED_KEY, 0, 19)]

        return {
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "active_requests": active,
            "total_requests": total,
            "success_requests": success,
            "failed_requests": failed_count,
            "downloads": {"active": downloads_active, "queued": downloads_queued, "max": 4},
            "top_paths": top_paths[:8],
            "recent": recent,
            "failed_list": failed_list,
        }
    except Exception as e:
        print(f"[monitor] Redis snapshot error: {e}")
        return {
            "uptime": "unknown",
            "active_requests": 0,
            "total_requests": 0,
            "success_requests": 0,
            "failed_requests": 0,
            "downloads": {"active": downloads_active, "queued": downloads_queued, "max": 4},
            "top_paths": [],
            "recent": [],
            "failed_list": [],
        }