"""Assemble full main module from gzip+base64 blob.

Phase 139 recovery. Developed by BAHATI GAD WANGWE.
"""
from __future__ import annotations

import base64
import gzip
from pathlib import Path

_PARTS_DIR = Path(__file__).resolve().parent


def load_main_source() -> str:
    single = _PARTS_DIR / "_main_full.b64"
    if single.exists():
        payload = single.read_text().strip()
    else:
        chunks: list[str] = []
        i = 0
        while True:
            p = _PARTS_DIR / f"_main_blob_{i}.b64"
            if not p.exists():
                break
            chunks.append(p.read_text().strip())
            i += 1
        if not chunks:
            raise RuntimeError("MAIN_BLOB_MISSING")
        payload = "".join(chunks)
    raw = base64.b64decode(payload)
    return gzip.decompress(raw).decode("utf-8")


def install_into(globals_dict: dict) -> None:
    source = load_main_source()
    exec(compile(source, "app/main_restored.py", "exec"), globals_dict)
