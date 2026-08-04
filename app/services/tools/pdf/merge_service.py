from typing import List

import pikepdf

from app.services.tools.pdf import common

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_FILES = 10
ALLOWED_CONTENT_TYPES = {"application/pdf"}


def _merge(input_paths: List[str], output_path: str) -> None:
    with pikepdf.Pdf.new() as target:
        for path in input_paths:
            with pikepdf.Pdf.open(path) as src:
                target.pages.extend(src.pages)
        target.save(output_path)


async def merge(contents: List[bytes], base_url: str) -> str:
    """Merges PDFs in the given order. Returns the download URL of the merged file."""
    input_paths = [await common.save_upload(content) for content in contents]
    output_path, download_url = common.make_output_path(base_url, prefix="merged")

    try:
        await common.run_cpu_bound(_merge, input_paths, output_path)
    except Exception:
        common.cleanup(output_path)
        raise
    finally:
        common.cleanup(*input_paths)

    return download_url
