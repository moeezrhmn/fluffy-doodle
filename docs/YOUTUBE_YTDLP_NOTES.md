# YouTube yt-dlp Notes (2025)

## Why Audio/Video Extraction Breaks

YouTube deployed two major changes in 2024-2025:
1. **n-challenge (nsig)** — JS must be executed by a real runtime (Deno/Node). Python-only solving no longer works.
2. **PO Tokens (Proof of Origin)** — most clients now require tokens. Without them, DASH URLs are missing or return 403.

## Client Status

Client names are not stable across yt-dlp releases. An unknown name is **not an error** — yt-dlp logs `WARNING: [youtube] Skipping unsupported client "<name>"` and silently falls back to its defaults (currently `visionos`, `web`), which return DASH-only formats. Check the live list before trusting anything below:

```bash
python3 -c "from yt_dlp.extractor.youtube import _base as b; print(list(b.INNERTUBE_CLIENTS))"
```

| Client | Status | Notes |
|---|---|---|
| `android`, `mweb`, `tv_simply` | ✅ Used by `video_info` | Each still serves format 18 (360p combined) — the only muxed format left, and the only kind `video_info`'s filter keeps. |
| `web` | ✅ Works | Needs EJS solver 0.8.0 + Deno. Best DASH audio/video, but DASH is video-only/audio-only — no muxed format. |
| `tv_embedded` | ❌ Removed | Gone as of yt-dlp 2026.08.19. Was the configured client; its removal is what emptied `available_formats`. |
| `tv` | ❌ Avoid | DRM experiment (issue #12563) returns only storyboard images. |
| `ios` | ❌ Avoid | Requires GVS PO Token. Also ignores cookies silently. |
| `android_music` | ❌ Unsupported | Current yt-dlp skips it. |

## Current Config

`video_info` ([app/services/tools/socials/youtube_service.py](../app/services/tools/socials/youtube_service.py)):

```python
'extractor_args': {'youtube': {'player_client': ['android', 'mweb', 'tv_simply']}},
'js_runtimes': {'deno': {}},      # dict format required
'remote_components': ['ejs:npm'], # list format required — string breaks it
```

`get_audio_url` sets no `player_client` and runs on yt-dlp's defaults, which is fine — it wants audio-only DASH, which the defaults do return.

## The muxed-format constraint

`video_info` filters to formats with `audio_channels is not None` and a real resolution — i.e. progressive/muxed only — because the endpoint hands back a single direct URL and never merges anything server-side. YouTube now serves exactly one such format (18, 360p) and only on some clients. If YouTube drops format 18 entirely, this endpoint cannot be fixed by swapping clients; it would need to either return separate video+audio URLs (a breaking change for callers) or download and mux with ffmpeg into a Lane B job.

## Required Server Setup

```bash
# Install yt-dlp WITH the EJS solver package (critical — plain yt-dlp ships without it)
pip install -U "yt-dlp[default]"

# Deno must be installed and on PATH
deno --version  # must be >= 2.3.0
deno upgrade    # if older
```

## Common Errors & Causes

| Error | Cause | Fix |
|---|---|---|
| `Challenge solver 0.3.2 not supported (needs 0.8.0)` | `yt-dlp-ejs` not installed | `pip install -U "yt-dlp[default]"` |
| `Ignoring unsupported remote component(s): e, j, s...` | `remote_components` is a string, not list | Change to `['ejs:github']` |
| `Invalid js_runtimes format` | `js_runtimes` is a string | Change to `{'deno': {}}` |
| `The page needs to be reloaded` | `player_skip=['js']` used — YouTube detects JS skipped | Never use `player_skip=['js']` |
| `Some tv client formats skipped as DRM protected` | YouTube DRM A/B test on tv client | Switch to `web` client |
| `Sign in to confirm you're not a bot` | IP flagged or PO token missing | Use residential proxy + EJS solver |

## Long-term: PO Token Provider (when `web` client needs tokens)

If `web` client starts requiring PO tokens, set up `bgutil-ytdlp-pot-provider`:

```bash
pip install bgutil-ytdlp-pot-provider
docker run -d --restart unless-stopped -p 4416:4416 brainicism/bgutil-ytdlp-pot-provider:deno
```

Then add to yt-dlp options:
```python
'extractor_args': {
    'youtube': {'player_client': ['mweb']},
    'youtubepot-bgutilhttp': {'base_url': ['http://127.0.0.1:4416']},
},
```

## Cannot Use

- Cookies for YouTube (hard constraint)