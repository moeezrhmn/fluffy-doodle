# PDF Tools API — Integration Guide

This is the backend for FileMutate's PDF tools. It does the actual file processing; it does not serve HTML pages or handle end users directly. All endpoints live under `/tools/pdf/*`.

## Base URL

Local dev: `http://localhost:8000` (or whatever port `uvicorn`/`gunicorn` is bound to).

## Authentication

Same scheme as every other endpoint in this API: a JWT bearer token, obtained via `POST /users/login` and sent on every request as:

```
Authorization: Bearer <token>
```

```bash
TOKEN=$(curl -s -X POST "$BASE/users/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "<service-account-username>", "password": "<service-account-password>"}' \
  | jq -r .access_token)
```

**This should be a dedicated service-account user for FileMutate's Laravel backend to log in as** — not a real person's account. Public signup (`/users/signup`) is currently disabled, so this account has to be created directly (ask whoever manages this backend's database to insert one, the same way the seeded admin account was created).

Tokens are long-lived (`ACCESS_TOKEN_EXPIRE_MINUTES` — currently about a year), so in practice Laravel can log in once, cache the token, and reuse it rather than logging in per-request. Treat it as a secret regardless: store it server-side only.

> **Do not call this API directly from browser JavaScript.** If the token ships in frontend code, anyone can read it out of the network tab and use it. The intended integration is: browser → your app server (Laravel) → this API → response back through your app server → browser. Your app server holds the token; the browser never sees it.

Missing, malformed, or expired token → `401 Unauthorized`.

## Two kinds of endpoints

- **Fast endpoints** (Merge, Split, JPG↔PDF) respond synchronously — send the file(s), get the result back in the same response. No polling needed.
- **Compress** is queued — you get a `job_id` back immediately, then poll a separate status endpoint until it's done. This exists because compression can take longer than a typical HTTP timeout under load; don't hold a request open waiting for it.

## Common error shape

All errors return `{"detail": "<message>"}` with one of these status codes:

| Code | Meaning |
|---|---|
| 400 | Bad request — missing/invalid parameter (e.g. bad page range, unknown preset) |
| 401 | Missing, malformed, or expired bearer token |
| 404 | Job not found (Compress only) |
| 413 | File exceeds the size limit for that endpoint |
| 415 | Wrong content type (e.g. sending a `.png` to an endpoint that only accepts PDFs) |
| 422 | The file was valid but processing failed (e.g. corrupt/unreadable PDF) |
| 429 | Compress queue is full — back off and retry shortly |

All successful downloads are served from `/downloads/<file>` on this same host — the `download_url`/`zip_url` fields in responses are already-complete URLs, ready to use directly (proxy them through your own backend if you don't want to expose this host to the browser).

---

## `POST /tools/pdf/merge`

Merges 2+ PDFs into one, in the order the files are given.

**Request:** `multipart/form-data`
| Field | Type | Notes |
|---|---|---|
| `files` | file[] | 2–10 PDFs, 50MB each max, `application/pdf` only |

**Response `200`:**
```json
{ "download_url": "http://.../downloads/<uuid>_merged.pdf" }
```

```bash
curl -X POST "$BASE/tools/pdf/merge" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@a.pdf;type=application/pdf" \
  -F "files=@b.pdf;type=application/pdf"
```

---

## `POST /tools/pdf/split`

Splits one PDF by explicit page ranges or into fixed-size chunks.

**Request:** `multipart/form-data`
| Field | Type | Notes |
|---|---|---|
| `file` | file | one PDF, 50MB max |
| `ranges` | string | e.g. `"1-3,5,8-10"` (1-indexed, inclusive). Provide this **or** `every_n`. |
| `every_n` | int | split into chunks of N pages each. Provide this **or** `ranges`. |
| `output` | string | `"files"` (default) or `"zip"` |

**Response `200`** (`output=files`):
```json
{ "files": ["http://.../downloads/<uuid>_split-1.pdf", "http://.../downloads/<uuid>_split-2.pdf"] }
```
**Response `200`** (`output=zip`):
```json
{ "zip_url": "http://.../downloads/<uuid>_split.zip" }
```

```bash
curl -X POST "$BASE/tools/pdf/split" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@doc.pdf;type=application/pdf" \
  -F "ranges=1-3,5,8-10" \
  -F "output=files"
```

---

## `POST /tools/pdf/jpg-to-pdf`

Converts one or more JPG/PNG images into a single PDF (one page per image, in the order given).

**Request:** `multipart/form-data`
| Field | Type | Notes |
|---|---|---|
| `files` | file[] | 1–30 images, 25MB each max, `image/jpeg` or `image/png` only |

**Response `200`:**
```json
{ "download_url": "http://.../downloads/<uuid>_images-to-pdf.pdf" }
```

---

## `POST /tools/pdf/pdf-to-jpg`

Renders each page of a PDF as an image.

**Request:** `multipart/form-data`
| Field | Type | Default | Notes |
|---|---|---|---|
| `file` | file | — | one PDF, 50MB max, up to 50 pages |
| `format` | string | `"jpg"` | `"jpg"` or `"png"` |
| `dpi` | int | `150` | 72–300 |
| `output` | string | `"files"` | `"files"` or `"zip"` |

**Response `200`** — same `files`/`zip_url` shape as Split above.

A PDF over 50 pages returns `400` with a clear message rather than attempting the render (there's no queued fallback for this endpoint yet — keep uploads under that limit).

---

## `POST /tools/pdf/compress`

Queues a PDF for compression (Ghostscript). **Async — see the job endpoints below.**

**Request:** `multipart/form-data`
| Field | Type | Default | Notes |
|---|---|---|---|
| `file` | file | — | one PDF, 100MB max |
| `preset` | string | `"recommended"` | `"low"`, `"recommended"`, or `"extreme"` (increasing compression, decreasing quality) |

**Response `200`:**
```json
{ "job_id": "8230f991-65b3-4b6c-b827-705237388249", "status": "queued", "position": 1 }
```

`429` if the compress queue is already at capacity — retry after a short delay.

### `GET /tools/pdf/compress/job/{job_id}`

Poll this until `status` is `"done"` or `"error"`. A reasonable polling interval is every 1–2 seconds.

**Response shape depends on `status`:**

```json
// queued
{ "job_id": "...", "status": "queued", "position": 2 }

// processing
{ "job_id": "...", "status": "processing" }

// done
{
  "job_id": "...",
  "status": "done",
  "download_url": "http://.../downloads/<uuid>_compressed.pdf",
  "size_before": 1789365,
  "size_after": 612480
}

// error
{ "job_id": "...", "status": "error", "error": "<message>" }
```

`404` if the job doesn't exist (never existed, or its result already expired — job records are kept for 2 hours).

### `DELETE /tools/pdf/compress/job/{job_id}`

Cancels/removes a job and cleans up its files. Returns `400` if the job is currently `processing` (can't cancel mid-run — poll until it finishes, then delete if you don't need the result). Returns `{"job_id": "...", "deleted": true}` on success.

```bash
# 1. submit
JOB_ID=$(curl -s -X POST "$BASE/tools/pdf/compress" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@big.pdf;type=application/pdf" \
  -F "preset=recommended" | jq -r .job_id)

# 2. poll
until curl -s -H "Authorization: Bearer $TOKEN" "$BASE/tools/pdf/compress/job/$JOB_ID" | grep -q '"status":"done"'; do
  sleep 1
done

# 3. download_url is now in the last poll response
```

---

## Notes for whoever's building the upload UI

- All file inputs are `multipart/form-data` — standard `FormData` in JS, no special encoding needed.
- None of these endpoints require the caller to pre-know the output filename — always read `download_url`/`zip_url`/`files` from the response, they're generated per-request.
- Uploaded/processed files aren't kept forever — Compress job records expire after 2 hours, and output files in `downloads/` are expected to be pulled promptly and then cleaned up on your side (per FileMutate's own ~1 hour retention policy). Don't treat `download_url` as a stable, long-lived link.
- `preset`/`format`/`output` are validated server-side, but validating them client-side too (e.g. a `<select>` instead of free text) avoids a round-trip for an obvious `400`.
