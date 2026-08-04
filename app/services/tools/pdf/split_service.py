import os
import zipfile
from typing import List, Optional, Tuple

import pikepdf

from app.services.tools.pdf import common

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"application/pdf"}


def parse_ranges(ranges: str, page_count: int) -> List[Tuple[int, int]]:
    """Parses "1-3,5,7-9" (1-indexed, inclusive) into 0-indexed (start, end) tuples."""
    parsed = []
    for part in ranges.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start, end = int(start_s), int(end_s)
        else:
            start = end = int(part)

        if start < 1 or end > page_count or start > end:
            raise ValueError(f"Invalid range '{part}' for a {page_count}-page document.")
        parsed.append((start - 1, end - 1))
    if not parsed:
        raise ValueError("No valid ranges provided.")
    return parsed


def every_n_ranges(n: int, page_count: int) -> List[Tuple[int, int]]:
    if n < 1:
        raise ValueError("every_n must be at least 1.")
    return [(i, min(i + n, page_count) - 1) for i in range(0, page_count, n)]


def _split(input_path: str, ranges: List[Tuple[int, int]], output_paths: List[str]) -> None:
    with pikepdf.Pdf.open(input_path) as src:
        for (start, end), output_path in zip(ranges, output_paths):
            with pikepdf.Pdf.new() as part:
                part.pages.extend(src.pages[start:end + 1])
                part.save(output_path)


def _page_count(input_path: str) -> int:
    with pikepdf.Pdf.open(input_path) as src:
        return len(src.pages)


def _zip(output_paths: List[str], zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in output_paths:
            zf.write(path, arcname=os.path.basename(path))


async def split(
    content: bytes,
    ranges: Optional[str],
    every_n: Optional[int],
    output: str,
    base_url: str,
) -> dict:
    """Splits a PDF by explicit ranges or every N pages. Returns {"files": [urls]} or {"zip_url": url}."""
    input_path = await common.save_upload(content)
    output_paths: List[str] = []

    try:
        page_count = await common.run_cpu_bound(_page_count, input_path)

        if ranges:
            page_ranges = parse_ranges(ranges, page_count)
        elif every_n:
            page_ranges = every_n_ranges(every_n, page_count)
        else:
            raise ValueError("Provide either 'ranges' or 'every_n'.")

        part_outputs = [
            common.make_output_path(base_url, prefix=f"split-{i + 1}")
            for i in range(len(page_ranges))
        ]
        output_paths = [p[0] for p in part_outputs]
        download_urls = [p[1] for p in part_outputs]

        await common.run_cpu_bound(_split, input_path, page_ranges, output_paths)

        if output == "zip":
            zip_path, zip_url = common.make_output_path(base_url, suffix=".zip", prefix="split")
            try:
                await common.run_cpu_bound(_zip, output_paths, zip_path)
            except Exception:
                common.cleanup(zip_path)
                raise
            finally:
                common.cleanup(*output_paths)
            return {"zip_url": zip_url}

        return {"files": download_urls}
    except Exception:
        common.cleanup(*output_paths)
        raise
    finally:
        common.cleanup(input_path)
