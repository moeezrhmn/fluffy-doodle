# Compress: add optional target-size input

## Context

The gap-analysis doc (`~/Downloads/filemutate-tool-gaps.md`) flags exact-target-size compression ("compress pdf to 100kb") as the #1 differentiator — competitors only offer a quality slider. Our current `POST /tools/pdf/compress` is exactly that slider (`low`/`recommended`/`extreme`). Concern raised: forcing a huge file (100MB+) down to a tiny target (e.g. 200KB) can produce a useless result if done blindly — so this shouldn't silently chase an impossible number.

**Decision:** keep the three presets as the default path (no regression), and add an optional target size that overrides them when given. If the target can't realistically be hit, return the best-effort result with a clear `target_met: false` rather than looping forever or degrading the file past usefulness.

## How it works

`app/services/tools/pdf/compress_service.py`:
- Extend `PRESETS`-style rungs with 1–2 more aggressive steps beyond today's `extreme` (lower resolution / more aggressive `-dColorImageResolution`), so there's real headroom past what exists now.
- New `_run_ghostscript_to_target(input_path, output_path, target_bytes)`: steps through the rungs from gentlest to most aggressive, running `_run_ghostscript` (already exists) at each, stopping as soon as `os.path.getsize(output_path) <= target_bytes`. Hard cap at ~5 attempts total (bounded worker time — this runs inside the existing Lane B job, so extra passes just make that one job take longer, not block anything else).
- If `target_bytes >= size_before`: skip compression, copy the file through as-is (nothing to do).
- If exhausted without reaching target: keep the smallest output achieved, mark `target_met = False`.
- `PdfCompressJob` gets two new fields: `target_size_kb: Optional[int]`, `target_met: Optional[bool]`.
- `_process()` branches: `target_size_kb` set → run the rung-stepping path; else → today's single-preset path (unchanged).

`app/controllers/tools/pdf_controller.py` (`compress_pdf`):
- New optional form field `target_size_kb: Optional[int] = Form(None)`.
- Validate: reject `< 10` (KB) outright with `400` — no real PDF is usefully compressible below that; nothing to attempt.
- `preset` becomes optional/ignored when `target_size_kb` is provided (still required — default `"recommended"` — when it isn't, exactly as today).

`GET /tools/pdf/compress/job/{job_id}`: `done` response includes `target_size_kb`/`target_met` when a target was requested (omitted otherwise, matching today's shape for preset-only calls).

`docs/PDF_TOOLS_API.md`: update the Compress section — new field, new response fields, and a short note on the "best effort, not guaranteed" behavior for unreachable targets.

## What's explicitly out of scope here

HEIC support, split-by-target-size, and unpaywalled batch processing (gap doc items #2–#4) are separate follow-ups, not part of this change.

## Verification

- Regression: existing preset-only calls (no `target_size_kb`) behave identically — same request/response shape as today.
- Real image-heavy PDF (like the ones used in prior Compress testing) at a generous target (easily hit on first rung), a tight-but-realistic target (hit after a few rungs), and a deliberately impossible target (e.g. 5KB on a multi-MB scan) — confirm `target_met` is `true`/`true`/`false` respectively, and the impossible case still returns a valid, usable PDF rather than an error.
- `target_size_kb=5` (below the 10KB floor) → `400` immediately, no job created.
