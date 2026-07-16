import time
from collections import deque
from threading import Lock

_lock = Lock()

_stats = {
    "active_requests": 0,
    "total_requests": 0,
    "success_requests": 0,
    "failed_requests": 0,
    "start_time": time.time(),
}

_recent: deque = deque(maxlen=100)
_path_stats: dict = {}


def request_started(path: str, method: str, region: str, video_url: str) -> dict:
    with _lock:
        _stats["active_requests"] += 1
        _stats["total_requests"] += 1
    return {
        "path": path,
        "method": method,
        "region": region or "-",
        "url": video_url or "-",
        "started_at": time.time(),
        "status": None,
        "duration_ms": None,
    }


def request_finished(entry: dict, status_code: int):
    with _lock:
        _stats["active_requests"] = max(0, _stats["active_requests"] - 1)
        if status_code < 400:
            _stats["success_requests"] += 1
        else:
            _stats["failed_requests"] += 1

        entry["status"] = status_code
        entry["duration_ms"] = round((time.time() - entry["started_at"]) * 1000)

        path = entry["path"]
        if path not in _path_stats:
            _path_stats[path] = {"total": 0, "failed": 0}
        _path_stats[path]["total"] += 1
        if status_code >= 400:
            _path_stats[path]["failed"] += 1

        _recent.appendleft(dict(entry))


def get_snapshot(downloads_active: int, downloads_queued: int) -> dict:
    with _lock:
        uptime = int(time.time() - _stats["start_time"])
        hours, rem = divmod(uptime, 3600)
        minutes, seconds = divmod(rem, 60)
        return {
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "active_requests": _stats["active_requests"],
            "total_requests": _stats["total_requests"],
            "success_requests": _stats["success_requests"],
            "failed_requests": _stats["failed_requests"],
            "downloads": {
                "active": downloads_active,
                "queued": downloads_queued,
                "max": 3,
            },
            "top_paths": sorted(
                [{"path": p, **v} for p, v in _path_stats.items()],
                key=lambda x: x["total"],
                reverse=True,
            )[:8],
            "recent": list(_recent)[:30],
        }