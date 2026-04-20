"""Byte bigram feature extraction for malware family discrimination."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from constants import TOP_BIGRAM_INDICES


def extract_ngram_features(file_path: Path) -> dict[str, Any]:
    """Extract a 256-dimensional log-scaled byte bigram vector from a file."""

    path = Path(file_path)
    data = path.read_bytes()
    if len(data) < 2:
        return {"ngram_vector": [0.0] * 256}

    byte_array = np.frombuffer(data, dtype=np.uint8).astype(np.uint16)
    bigrams = (byte_array[:-1] << 8) | byte_array[1:]
    counts = np.bincount(bigrams, minlength=65536).astype(np.float32)
    probabilities = counts / max(len(byte_array), 1)
    scaled = np.log1p(probabilities)
    selected = scaled[np.array(TOP_BIGRAM_INDICES, dtype=np.int32)]

    return {"ngram_vector": [round(float(value), 8) for value in selected.tolist()]}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract 256 byte-bigram features.")
    parser.add_argument("file_path", type=Path, help="Path to the binary file")
    args = parser.parse_args()

    result = extract_ngram_features(args.file_path)
    print(json.dumps(result, indent=2))
