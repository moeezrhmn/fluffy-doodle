# YouTube yt-dlp Notes (2025)

## Why Audio/Video Extraction Breaks

YouTube deployed two major changes in 2024-2025:
1. **n-challenge (nsig)** — JS must be executed by a real runtime (Deno/Node). Python-only solving no longer works.
2. **PO Tokens (Proof of Origin)** — most clients now require tokens. Without them, DASH URLs are missing or return 403.

## Client Status

| Client | Status | Notes |
|---|---|---|
| `web` | ✅ Works | Needs EJS solver 0.8.0 + Deno. Best DASH audio/video. |
| `android` | ⚠️ Limited | SABR experiment strips DASH URLs. Only returns format 18 (360p combined). |
| `tv` | ❌ Avoid | DRM experiment (issue #12563) returns only storyboard images. |
| `ios` | ❌ Avoid | Requires GVS PO Token. Also ignores cookies silently. |
| `android_music` | ❌ Unsupported | Current yt-dlp skips it. |

## Current Config (video_info + get_audio_url)

```python
'extractor_args': {'youtube': {'player_client': ['web', 'android']}},
'js_runtimes': {'deno': {}},        # dict format required
'remote_components': ['ejs:github'], # list format required — string breaks it
```

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