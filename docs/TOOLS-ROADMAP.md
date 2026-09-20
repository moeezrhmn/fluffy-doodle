# FileMutate — Tools Roadmap & Status

Full tool inventory, organized to match the category structure competitors (iLovePDF, Smallpdf) actually use in their nav, so it's easy to see at a glance what's shipped vs. planned vs. not yet scoped. This supersedes the old tier-only view — each table still notes which build tier a planned tool belongs to, so the original build-order reasoning isn't lost.

**Status legend:** ✅ Live · 🔧 Planned · 🆕 New gap (not in any previous version of this roadmap)

**Where this is built:** all backend endpoints live in `fluffy-doodle` (a separate Python/FastAPI repo — see that repo's `docs/PDF_TOOLS_API.md` for the actual integration contract). Endpoint paths below reflect the real, shipped convention (`/tools/pdf/...`), not the original `/v1/...` sketch from early planning.

---

## Organize PDF

| Tool | Status | Endpoint | Python approach | Tier | Effort |
|---|---|---|---|---|---|
| Merge PDF | ✅ Live | `POST /tools/pdf/merge` | `pikepdf`, straight page concatenation | 1 | S |
| Split PDF | ✅ Live | `POST /tools/pdf/split` | `pikepdf`, by page ranges or every N pages, files or zip output | 1 | S |
| Remove pages | 🔧 Planned | `POST /tools/pdf/remove-pages` | `pikepdf` | 3 | S |
| Extract pages | 🔧 Planned | `POST /tools/pdf/extract-pages` | `pikepdf` | 3 | S |
| Organize PDF (reorder pages) | 🔧 Planned | `POST /tools/pdf/organize` | `pikepdf` | 3 | S |
| Scan to PDF | 🆕 New gap | — | Camera capture + auto edge-detection/perspective correction (e.g. OpenCV, already a dependency) + `img2pdf`. Distinct from plain JPG→PDF — no image correction pipeline exists today. | — | M |

## Optimize PDF

| Tool | Status | Endpoint | Python approach | Tier | Effort |
|---|---|---|---|---|---|
| Compress PDF | ✅ Live (presets only) | `POST /tools/pdf/compress` (+ job polling) | `pikepdf` + Ghostscript, `low`/`recommended`/`extreme` presets | 1 | M |
| ↳ Compress to exact target size | 🔧 Planned | same endpoint, new `target_size_kb` field | See `fluffy-doodle/docs/COMPRESS_TARGET_SIZE_PLAN.md` | — | M |
| Repair PDF | 🔧 Planned | `POST /tools/pdf/repair` | `pikepdf`/`qpdf` structural repair | 5 | S–M |
| OCR PDF | 🔧 Planned | `POST /tools/pdf/ocr` (job queue) | `ocrmypdf` (wraps Tesseract) — needs Tesseract on the worker | 5 | M |

## Convert to PDF

| Tool | Status | Endpoint | Python approach | Tier | Effort |
|---|---|---|---|---|---|
| JPG to PDF | ✅ Live (PNG too) | `POST /tools/pdf/jpg-to-pdf` | `img2pdf`, lossless | 1 | S |
| Word to PDF | 🔧 Planned | `POST /tools/pdf/convert/word-to-pdf` (job queue) | LibreOffice headless (`soffice --convert-to pdf`) | 2 | M |
| PowerPoint to PDF | 🔧 Planned | `POST /tools/pdf/convert/ppt-to-pdf` (job queue) | LibreOffice headless (same worker as Word→PDF) | 2 | S |
| Excel to PDF | 🔧 Planned | `POST /tools/pdf/convert/excel-to-pdf` (job queue) | LibreOffice headless (same worker) | 2 | S |
| HTML to PDF | 🔧 Planned | `POST /tools/pdf/convert/html-to-pdf` (job queue) | Headless Chromium via `Playwright` (already a dependency) | 5 | M |

## Convert from PDF

| Tool | Status | Endpoint | Python approach | Tier | Effort |
|---|---|---|---|---|---|
| PDF to JPG | ✅ Live (PNG too, DPI configurable) | `POST /tools/pdf/pdf-to-jpg` | `PyMuPDF` rendering, files or zip output | 1 | S–M |
| PDF to Word | 🔧 Planned | `POST /tools/pdf/convert/pdf-to-word` (job queue) | `pdf2docx` — layout fidelity varies on complex PDFs | 2 | M–L |
| PDF to PowerPoint | 🔧 Planned | `POST /tools/pdf/convert/pdf-to-ppt` (job queue) | Weak fidelity via `pdf2docx`-style extraction — evaluate `Spire.Presentation` before committing | 2 | L |
| PDF to Excel | 🔧 Planned | `POST /tools/pdf/convert/pdf-to-excel` (job queue) | Table extraction via `camelot`/`pdfplumber` → `openpyxl` — quality depends on real table structure vs. scanned image | 2 | L |
| PDF to PDF/A | 🆕 New gap | — | Ghostscript (`-dPDFA=2`) or `pikepdf` — worth checking if a straightforward Ghostscript flag covers this before reaching for anything heavier | — | S–M |

## Edit PDF

| Tool | Status | Endpoint | Python approach | Tier | Effort |
|---|---|---|---|---|---|
| Rotate PDF | 🔧 Planned | `POST /tools/pdf/rotate` | `pikepdf` | 3 | S |
| Add page numbers | 🔧 Planned | `POST /tools/pdf/page-numbers` | `pikepdf` + `reportlab` overlay | 3 | S |
| Add watermark | 🔧 Planned | `POST /tools/pdf/watermark` | `pikepdf` + `reportlab` overlay | 3 | S |
| Crop PDF | 🔧 Planned | `POST /tools/pdf/crop` | `pikepdf` (mediabox adjustment) | 3 | S |
| Edit PDF (full text editor) | 🔧 Planned, low priority | — | No good open-source path — realistically a licensed SDK or a much larger custom effort. Don't scope until the rest of the catalog is live and there's clear demand. | 5 | XL |
| PDF Forms (fill & flatten) | 🆕 New gap | — | Form field detection/fill via `pypdf`/`pikepdf` (AcroForm support) or `PyMuPDF`; flatten by rendering filled values into the page content. Common for job applications, visa/government forms — flagged as a top gap-analysis item. | — | M–L |

Rotate/Remove/Extract/Organize/Page-numbers/Watermark/Crop are all thin wrappers around the same `pikepdf` page-manipulation toolkit — build as one shared "page ops" module rather than seven separate scripts (per original Tier 3 plan).

## PDF Security

| Tool | Status | Endpoint | Python approach | Tier | Effort |
|---|---|---|---|---|---|
| Unlock PDF | 🔧 Planned | `POST /tools/pdf/unlock` | `pikepdf` (requires the current password) | 4 | S |
| Protect PDF | 🔧 Planned | `POST /tools/pdf/protect` | `pikepdf` (AES encryption) | 4 | S |
| Sign PDF | 🔧 Planned | `POST /tools/pdf/sign` | Visual: `PyMuPDF`/`pikepdf` to place a drawn/uploaded signature image. Certificate-based (if pursued): `pyHanko` for real cryptographic signing. | 4 | M (visual) / L (certificate) |
| Redact PDF | 🔧 Planned | `POST /tools/pdf/redact` | `PyMuPDF` — must remove underlying text, not just draw a black box over it | 4 | M–L |
| Compare PDF | 🔧 Planned | `POST /tools/pdf/compare` (job queue) | `pdfplumber` text diff (visual diff is a much bigger effort — scope text-only first) | 5 | M–L |

## PDF Intelligence

Entirely new category — not in any previous version of this roadmap. All three need an LLM/AI backend; this app already has `HUGGING_FACE_API_KEY` wired up and an existing AI-integration pattern (`ai_detection.py`, GoWinston) to follow.

| Tool | Status | Endpoint | Python approach | Effort |
|---|---|---|---|---|
| AI Summarizer | 🆕 New gap | `POST /tools/pdf/summarize` (job queue) | Extract text (`pdfplumber`/`PyMuPDF`) → LLM summarization call | M |
| Translate PDF | 🆕 New gap | `POST /tools/pdf/translate` (job queue) | Extract text → LLM/translation API → re-render or return translated text/PDF | M–L |
| PDF to Markdown | 🆕 New gap | `POST /tools/pdf/to-markdown` | Text/structure extraction (`PyMuPDF`) → Markdown formatting — no LLM strictly required, cheaper than the other two | S–M |

---

## Not on FileMutate's roadmap by design

Both iLovePDF and Smallpdf have expanded into a general **image toolkit** (compress/resize/crop/convert image, remove background, upscale) and Smallpdf specifically also has **Grayscale PDF**. FileMutate's brand positioning (`PLAN.md`) is explicitly a PDF toolkit, so these are treated as a deliberate scope decision, not an oversight — worth revisiting only if there's a specific reason to compete on that dimension.

---

## Status summary

**Live (5):** Merge, Split, Compress (presets), JPG→PDF, PDF→JPG.

**Planned, already scoped (Tiers 2–5, 22 tools):** everything else that was in the original tier list — Office conversions, page-ops (rotate/organize/remove/extract/page-numbers/watermark/crop), security/sign/redact/compare, OCR/repair/HTML-to-PDF.

**New gaps found against the current competitor tool menu (6):** Scan to PDF, PDF to PDF/A, PDF Forms (fill & flatten), AI Summarizer, Translate PDF, PDF to Markdown.

**Suggested next build order** (per current discussion): Tier 3 (page ops) → Tier 4 (security/sign) → Tier 2 (Office conversions, needs a new LibreOffice-headless worker) → fold in the 6 new gaps and Tier 5 as capacity allows. Compress-to-exact-size (see `COMPRESS_TARGET_SIZE_PLAN.md`) is a separate, already-planned enhancement to a tool that's already live.