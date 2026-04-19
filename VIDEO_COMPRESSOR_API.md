# Video Compressor API — Frontend Integration Guide

Base URL: `http://YOUR_SERVER/` (same as existing social downloader API)
Auth: `Authorization: Bearer {token}` header required on all requests.

---

## Flow Overview

```
1. POST /tools/media/compress-video   →  get job_id
2. GET  /tools/media/job/{job_id}     →  poll until status = "done"
3. GET  /tools/media/job/{job_id}/download  →  stream/download the file
4. DELETE /tools/media/job/{job_id}   →  cleanup (call after user downloads)
```

---

## 1. Submit Compression Job

**POST** `/tools/media/compress-video`
Content-Type: `multipart/form-data`

| Field | Type | Required | Description |
|---|---|---|---|
| `file` | File | Yes | Video file (mp4, webm, mov, avi) — max 200MB |
| `preset` | string | No | `discord` / `whatsapp` / `email` / `custom` — default: `discord` |
| `target_mb` | integer | Only if `custom` | Target size in MB |

**Presets:**
| Preset | Target Size | Resolution Cap |
|---|---|---|
| `discord` | 25 MB | 1280x720 |
| `whatsapp` | 16 MB | 1280x720 |
| `email` | 10 MB | 854x480 |
| `custom` | `target_mb` value | original |

**Success Response `200`:**
```json
{
    "job_id": "1236eb0f-8ee7-40ac-a514-a0d33d1a53da",
    "status": "queued",
    "position": 1
}
```

**Error Responses:**
| Status | Reason |
|---|---|
| 400 | Invalid preset or missing `target_mb` for custom |
| 413 | File exceeds 200MB |
| 415 | Unsupported file type |

---

## 2. Poll Job Status

**GET** `/tools/media/job/{job_id}`

Poll this endpoint every **2–3 seconds** until `status` is `done` or `error`.

**Response when queued:**
```json
{
    "job_id": "1236eb0f-...",
    "status": "queued",
    "position": 2
}
```

**Response when processing:**
```json
{
    "job_id": "1236eb0f-...",
    "status": "processing"
}
```

**Response when done:**
```json
{
    "job_id": "1236eb0f-...",
    "status": "done",
    "download_url": "https://yourdomain.com/downloads/1236eb0f-..._compressed.mp4"
}
```

**Response when error:**
```json
{
    "job_id": "1236eb0f-...",
    "status": "error",
    "error": "FFmpeg error message"
}
```

**Status values:** `queued` → `processing` → `done` / `error`

---

## 3. Delete Job (Cleanup)

**DELETE** `/tools/media/job/{job_id}`

Call this after the user has successfully downloaded the file to free up server disk space.

**Success Response `200`:**
```json
{
    "job_id": "1236eb0f-...",
    "deleted": true
}
```

**Error Responses:**
| Status | Reason |
|---|---|
| 400 | Job is currently processing, cannot delete |
| 404 | Job not found |

---

## Notes

- If the uploaded video is **already smaller than the target size**, the API returns it as-is instantly (no re-encoding).
- Compression (2-pass encoding) can take **30 seconds to 3 minutes** depending on file size — poll accordingly.
- The server processes a **max of 2 jobs concurrently**. Additional jobs queue up — use the `position` field to show a queue indicator in the UI.
- Job state is **in-memory** — if the server restarts, job IDs are lost. Handle 404 on poll as a "please re-upload" case.
