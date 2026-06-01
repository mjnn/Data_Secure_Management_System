"""上传读取与文件名安全处理。"""

import re
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


def read_upload_with_limit(upload_file: UploadFile, max_bytes: int | None = None) -> bytes:
    limit = max_bytes if max_bytes is not None else settings.upload_max_bytes
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = upload_file.file.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ValueError("文件超过大小限制")
        chunks.append(chunk)
    return b"".join(chunks)


def safe_content_disposition_filename(name: str, fallback: str = "download") -> str:
    cleaned = re.sub(r'[\r\n"\\]', "", (name or fallback).strip()) or fallback
    return cleaned[:200]


def resolve_path_within_root(root: Path, relative: str) -> Path:
    base = root.resolve()
    if ".." in Path(relative).parts:
        raise ValueError("非法路径")
    target = (base / relative).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("非法路径") from exc
    return target
