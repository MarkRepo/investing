"""Convert PDF to markdown via MinerU Precision API (async polling).

Flow:
    1. POST /api/v4/file-urls/batch  — register file, get presigned PUT URL + batch_id
    2. PUT file to presigned URL     — MinerU auto-triggers parsing on upload complete
    3. Poll /api/v4/extract-results/batch/{batch_id} using the SAME batch_id from step 1
    4. Download markdown from result URL

Usage:
    python -m scripts.mineru_api path/to/file.pdf
    python -m scripts.mineru_api path/to/file.pdf --out path/to/output.md
    python -m scripts.mineru_api path/to/file.pdf --model vlm

Token is read from MINERU_TOKEN in .env file.
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path

import requests

log = logging.getLogger("mineru_api")


def _load_dotenv() -> None:
    env_file = Path(__file__).parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


_load_dotenv()

_BASE = "https://mineru.net"
_REGISTER_URL = f"{_BASE}/api/v4/file-urls/batch"
_RESULT_URL = f"{_BASE}/api/v4/extract-results/batch"
_POLL_INTERVAL = 5    # seconds
_TIMEOUT = int(os.environ.get("MINERU_TIMEOUT", "600"))  # seconds; override via env
_MAX_ATTEMPTS = int(os.environ.get("MINERU_MAX_ATTEMPTS", "3"))  # total tries on transient failure
_RETRY_BACKOFF = int(os.environ.get("MINERU_RETRY_BACKOFF", "10"))  # seconds between attempts


def _token() -> str:
    t = os.environ.get("MINERU_TOKEN", "")
    if not t:
        raise RuntimeError("MINERU_TOKEN not set — add it to .env")
    return t


def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}"}


def _register_and_get_upload_url(filename: str, file_size: int, model: str) -> tuple[str, str]:
    """Register file with MinerU, get (presigned_put_url, batch_id).

    Model settings are passed here — no separate task submission needed.
    MinerU auto-triggers parsing once the PUT upload completes.
    """
    payload = {
        "files": [{"name": filename, "data_id": Path(filename).stem}],
        "model_version": model,
        "is_ocr": False,
        "extra_formats": [],      # markdown is always included
        "enable_table": True,
        "language": "ch",
    }
    r = requests.post(_REGISTER_URL, json=payload, headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()["data"]
    return data["file_urls"][0], data["batch_id"]


def _upload_file(upload_url: str, path: Path) -> None:
    with path.open("rb") as f:
        r = requests.put(upload_url, data=f, timeout=120)
    r.raise_for_status()


def _poll_result(batch_id: str) -> dict:
    """Poll until the first file in the batch is done. Returns the file result dict."""
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        r = requests.get(f"{_RESULT_URL}/{batch_id}", headers=_headers(), timeout=30)
        r.raise_for_status()
        extract_result = r.json().get("data", {}).get("extract_result", [])
        if not extract_result:
            log.info("No results yet, waiting…")
            time.sleep(_POLL_INTERVAL)
            continue
        item = extract_result[0]
        state = item.get("state", "running")
        log.info("MinerU state=%s", state)
        if state == "done":
            return item
        if state in ("failed", "error"):
            raise RuntimeError(f"MinerU task failed: {item.get('err_msg', item)}")
        time.sleep(_POLL_INTERVAL)
    raise TimeoutError(f"MinerU did not complete within {_TIMEOUT}s")


def _download_and_extract(result: dict, out_dir: Path) -> Path:
    """Download result ZIP, extract all assets, return path to full.md.

    out_dir/
        full.md          ← returned
        images/
            *.jpg
        _content_list.json
        layout.json
    """
    import io
    import zipfile

    zip_url = result.get("full_zip_url", "")
    if not zip_url:
        raise RuntimeError(f"No full_zip_url in result: {result}")

    r = requests.get(zip_url, timeout=120)
    r.raise_for_status()

    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        zf.extractall(out_dir)

    md_path = out_dir / "full.md"
    if not md_path.exists():
        # Fallback: find any .md in the extracted dir
        md_files = list(out_dir.glob("*.md"))
        if not md_files:
            raise RuntimeError(f"No .md file after extraction. Contents: {list(out_dir.iterdir())}")
        md_path = md_files[0]

    return md_path


def _convert_once(pdf_path: Path, out_dir: Path, model: str) -> Path:
    """Run one full register → upload → poll → download cycle. Raises on failure."""
    filename = pdf_path.name
    file_size = pdf_path.stat().st_size

    log.info("Registering %s (%.1f MB, model=%s)…", filename, file_size / 1e6, model)
    upload_url, batch_id = _register_and_get_upload_url(filename, file_size, model)
    log.info("batch_id=%s", batch_id)

    log.info("Uploading to OSS…")
    _upload_file(upload_url, pdf_path)
    log.info("Upload complete — MinerU will auto-trigger parsing")

    log.info("Polling for result…")
    result = _poll_result(batch_id)

    log.info("Extracting ZIP to %s…", out_dir)
    md_path = _download_and_extract(result, out_dir)
    log.info("Written → %s (images in %s/images/)", md_path, out_dir.name)
    return md_path


def convert(pdf_path: Path, out_path: Path | None = None, model: str = "pipeline") -> Path:
    """Convert a PDF to markdown. Returns path to full.md inside the output directory.

    Output layout:
        {out_dir}/full.md      ← returned path
        {out_dir}/images/*.jpg ← referenced by full.md with relative paths
        {out_dir}/layout.json

    out_dir defaults to {pdf_path.stem}_mineru/ next to the PDF.
    If out_path is given it is used as the output directory.

    MinerU occasionally returns a transient parse failure ("parsing failed,
    please try again later"). Each attempt re-registers a fresh batch_id, since
    re-polling a failed batch never recovers. Tunable via MINERU_MAX_ATTEMPTS.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    out_dir = out_path or pdf_path.parent / f"{pdf_path.stem}_mineru"

    last_err: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _convert_once(pdf_path, out_dir, model)
        except (RuntimeError, TimeoutError, requests.RequestException) as exc:
            last_err = exc
            if attempt < _MAX_ATTEMPTS:
                log.warning(
                    "MinerU attempt %d/%d failed (%s) — retrying in %ds…",
                    attempt, _MAX_ATTEMPTS, exc, _RETRY_BACKOFF,
                )
                time.sleep(_RETRY_BACKOFF)
            else:
                log.error("MinerU attempt %d/%d failed (%s) — giving up", attempt, _MAX_ATTEMPTS, exc)
    raise RuntimeError(
        f"MinerU failed after {_MAX_ATTEMPTS} attempts for {pdf_path.name}: {last_err}"
    ) from last_err


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Convert PDF to markdown via MinerU API")
    parser.add_argument("pdf", type=Path, help="Input PDF file")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output directory (default: {pdf_stem}_mineru/ next to PDF)")
    parser.add_argument(
        "--model",
        choices=["pipeline", "vlm", "MinerU-HTML"],
        default="pipeline",
        help="MinerU model (default: pipeline)",
    )
    args = parser.parse_args()
    md_path = convert(args.pdf, args.out, args.model)
    print(f"✓ {md_path}")
    print(f"  images: {md_path.parent / 'images'}")


if __name__ == "__main__":
    main()
