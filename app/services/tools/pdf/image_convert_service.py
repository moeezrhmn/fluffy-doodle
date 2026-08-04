import os
import zipfile
from typing import List

import fitz  # PyMuPDF
import img2pdf

from app.services.tools.pdf import common

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024
MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024
MAX_IMAGES = 30
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
ALLOWED_PDF_TYPES = {"application/pdf"}

VALID_IMAGE_FORMATS = {"jpg", "png"}
DEFAULT_DPI = 150
MIN_DPI = 72
MAX_DPI = 300

# No Lane B queue yet — a hard cap stands in for the "escalate to a queued job"
# path described for oversized PDF-to-image renders.
MAX_RENDER_PAGES = common.PAGE_COUNT_ESCALATION_THRESHOLD


def _images_to_pdf(image_contents: List[bytes], output_path: str) -> None:
    pdf_bytes = img2pdf.convert(image_contents)
    with open(output_path, "wb") as f:
        f.write(pdf_bytes)


async def images_to_pdf(contents: List[bytes], base_url: str) -> str:
    """Converts one or more JPG/PNG images into a single PDF, one page per image."""
    output_path, download_url = common.make_output_path(base_url, prefix="images-to-pdf")

    try:
        await common.run_cpu_bound(_images_to_pdf, contents, output_path)
    except Exception:
        common.cleanup(output_path)
        raise

    return download_url


def _page_count(input_path: str) -> int:
    with fitz.open(input_path) as doc:
        return doc.page_count


def _render_pages(input_path: str, dpi: int, fmt: str, output_paths: List[str]) -> None:
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    with fitz.open(input_path) as doc:
        for page, output_path in zip(doc, output_paths):
            pix = page.get_pixmap(matrix=matrix)
            pix.save(output_path, output=fmt.upper())


def _zip(output_paths: List[str], zip_path: str) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in output_paths:
            zf.write(path, arcname=os.path.basename(path))


async def pdf_to_images(content: bytes, fmt: str, dpi: int, output: str, base_url: str) -> dict:
    """Renders each page of a PDF as an image. Returns {"files": [urls]} or {"zip_url": url}."""
    input_path = await common.save_upload(content)
    output_paths: List[str] = []

    try:
        page_count = await common.run_cpu_bound(_page_count, input_path)
        if page_count > MAX_RENDER_PAGES:
            raise ValueError(
                f"PDF has {page_count} pages; this endpoint supports up to {MAX_RENDER_PAGES} pages at a time."
            )

        suffix = f".{fmt}"
        part_outputs = [
            common.make_output_path(base_url, suffix=suffix, prefix=f"page-{i + 1}")
            for i in range(page_count)
        ]
        output_paths = [p[0] for p in part_outputs]
        download_urls = [p[1] for p in part_outputs]

        await common.run_cpu_bound(_render_pages, input_path, dpi, fmt, output_paths)

        if output == "zip":
            zip_path, zip_url = common.make_output_path(base_url, suffix=".zip", prefix="pages")
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