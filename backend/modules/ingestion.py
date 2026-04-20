"""File ingestion and Redis-backed caching for uploaded binaries."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import aiofiles
from fastapi import HTTPException, UploadFile
from redis.asyncio import Redis

from config import get_settings


MAX_UPLOAD_SIZE = 20 * 1024 * 1024


async def ingest_upload(upload: UploadFile, redis_client: Redis) -> dict[str, Any]:
    """Read an uploaded file, hash it, and short-circuit on Redis cache hits."""

    settings = get_settings()
    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds the 20MB upload limit.")

    sha256 = hashlib.sha256(content).hexdigest()
    cache_key = f"aegis:scan:{sha256}"
    cached = await redis_client.get(cache_key)
    if cached:
        return {
            "cache_hit": True,
            "sha256": sha256,
            "file_path": None,
            "cached_result": json.loads(cached),
        }

    file_path = settings.upload_dir / f"{sha256}.bin"
    async with aiofiles.open(file_path, "wb") as handle:
        await handle.write(content)

    return {
        "cache_hit": False,
        "sha256": sha256,
        "file_path": str(file_path),
        "cached_result": None,
    }


if __name__ == "__main__":
    import argparse
    import asyncio

    from redis.asyncio import from_url

    parser = argparse.ArgumentParser(description="Standalone ingestion smoke test.")
    parser.add_argument("file_path", type=Path, help="Path to a local file to simulate an upload")
    args = parser.parse_args()

    class LocalUpload:
        filename = args.file_path.name

        async def read(self) -> bytes:
            return args.file_path.read_bytes()

    async def _run() -> None:
        redis_client = from_url(get_settings().redis_url, decode_responses=True)
        result = await ingest_upload(LocalUpload(), redis_client)
        print(json.dumps(result, indent=2))
        await redis_client.aclose()

    asyncio.run(_run())
