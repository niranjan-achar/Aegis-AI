"""Binary-to-image conversion utilities for malware visualisation."""

from __future__ import annotations

import base64
import math
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from config import get_settings


def binary_file_to_image(file_path: Path, sha256: str | None = None) -> dict[str, Any]:
    """Convert a binary file into a 224x224 grayscale PNG and base64 payload."""

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Binary file not found: {path}")

    file_bytes = path.read_bytes()
    if not file_bytes:
        raise ValueError(f"Binary file is empty: {path}")

    byte_array = np.frombuffer(file_bytes, dtype=np.uint8)
    width = int(math.sqrt(byte_array.size))
    if width <= 1:
        raise ValueError("File is too small to form a square image.")

    trimmed = byte_array[: width * width]
    image_matrix = trimmed.reshape((width, width))
    image = Image.fromarray(image_matrix, mode="L").resize((224, 224), Image.Resampling.LANCZOS)

    settings = get_settings()
    image_name = f"{sha256 or path.stem}.png"
    image_path = settings.image_dir / image_name
    image.save(image_path, format="PNG")

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    image_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {"image_path": str(image_path), "image_b64": image_b64}


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Convert a binary file into a grayscale image.")
    parser.add_argument("file_path", type=Path, help="Path to the input .exe or .dll")
    parser.add_argument("--sha256", type=str, default=None, help="Optional SHA-256 filename override")
    args = parser.parse_args()

    result = binary_file_to_image(args.file_path, args.sha256)
    print(json.dumps(result, indent=2))
