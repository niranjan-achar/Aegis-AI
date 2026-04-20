"""PE header and import-table feature extraction for Windows executables."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pefile

from constants import SUSPICIOUS_API_VOCAB


def _entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256)
    probabilities = counts[counts > 0] / len(data)
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _normalise(value: float, min_value: float, max_value: float) -> float:
    if max_value <= min_value:
        return 0.0
    clamped = max(min_value, min(value, max_value))
    return float((clamped - min_value) / (max_value - min_value))


def _compress_import_vector(import_vector: np.ndarray, target_dim: int = 16) -> list[float]:
    bucket_size = math.ceil(import_vector.size / target_dim)
    features = []
    for index in range(target_dim):
        start = index * bucket_size
        end = min((index + 1) * bucket_size, import_vector.size)
        bucket = import_vector[start:end]
        features.append(float(bucket.mean()) if bucket.size else 0.0)
    return features


def extract_pe_features(file_path: Path) -> dict[str, Any]:
    """Extract a fixed 50-dimensional feature vector from a PE file."""

    path = Path(file_path)
    zero_result = {
        "feature_vector": [0.0] * 50,
        "is_pe": False,
        "imphash": "",
        "sections": [],
        "imports": {},
        "header_flags": {},
    }

    try:
        pe = pefile.PE(str(path))
    except (FileNotFoundError, pefile.PEFormatError, OSError):
        return zero_result

    section_details: list[dict[str, Any]] = []
    entropy_values: list[float] = []
    virtual_sizes: list[int] = []
    raw_sizes: list[int] = []

    for section in pe.sections:
        raw_data = section.get_data()
        entropy = _entropy(raw_data)
        name = section.Name.decode(errors="ignore").strip("\x00") or "unknown"
        virtual_size = int(section.Misc_VirtualSize)
        raw_size = int(section.SizeOfRawData)

        entropy_values.append(entropy)
        virtual_sizes.append(virtual_size)
        raw_sizes.append(raw_size)

        section_details.append(
            {
                "name": name,
                "entropy": round(entropy, 4),
                "virtual_size": virtual_size,
                "raw_size": raw_size,
            }
        )

    imported_names: set[str] = set()
    imports_by_dll: dict[str, list[str]] = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for entry in pe.DIRECTORY_ENTRY_IMPORT:
            dll_name = entry.dll.decode(errors="ignore") if entry.dll else "unknown"
            imports_by_dll[dll_name] = []
            for imp in entry.imports:
                if imp.name:
                    func_name = imp.name.decode(errors="ignore")
                    imports_by_dll[dll_name].append(func_name)
                    imported_names.add(func_name)

    import_presence = np.array(
        [1.0 if api in imported_names else 0.0 for api in SUSPICIOUS_API_VOCAB], dtype=np.float32
    )

    numeric_features = [
        _normalise(len(pe.sections), 0, 12),
        _normalise(float(pe.FILE_HEADER.TimeDateStamp), 0, 2_147_483_647),
        _normalise(float(getattr(pe.OPTIONAL_HEADER, "CheckSum", 0)), 0, 10_000_000),
        _normalise(float(getattr(pe.OPTIONAL_HEADER, "DllCharacteristics", 0)), 0, 65535),
        _normalise(float(np.mean(entropy_values) if entropy_values else 0.0), 0, 8),
        _normalise(float(np.max(entropy_values) if entropy_values else 0.0), 0, 8),
        _normalise(float(np.mean(virtual_sizes) if virtual_sizes else 0.0), 0, 500000),
        _normalise(float(np.mean(raw_sizes) if raw_sizes else 0.0), 0, 500000),
        _normalise(float(np.std(raw_sizes) if raw_sizes else 0.0), 0, 300000),
        _normalise(float(sum(raw_sizes)), 0, 20_000_000),
    ]

    # Fixed slots for up to 8 sections: entropy, virtual size, raw size, name hash summary.
    section_feature_vector: list[float] = []
    for index in range(8):
        if index < len(section_details):
            section = section_details[index]
            name_hash = int(hashlib.sha256(section["name"].encode("utf-8")).hexdigest()[:8], 16)
            section_feature_vector.extend(
                [
                    _normalise(section["entropy"], 0, 8),
                    _normalise(float(section["virtual_size"]), 0, 1_000_000),
                    _normalise(float(section["raw_size"]), 0, 1_000_000),
                    _normalise(float(name_hash), 0, 0xFFFFFFFF),
                ]
            )
        else:
            section_feature_vector.extend([0.0, 0.0, 0.0, 0.0])

    import_summary_features = _compress_import_vector(import_presence, target_dim=8)
    aggregate_import_features = [
        _normalise(float(import_presence.sum()), 0, len(SUSPICIOUS_API_VOCAB)),
        _normalise(float(len(imported_names)), 0, 512),
    ]

    feature_vector = numeric_features + section_feature_vector + import_summary_features + aggregate_import_features
    feature_vector = (feature_vector + [0.0] * 50)[:50]

    return {
        "feature_vector": [round(float(value), 6) for value in feature_vector],
        "is_pe": True,
        "imphash": pe.get_imphash() if hasattr(pe, "get_imphash") else "",
        "sections": section_details,
        "imports": imports_by_dll,
        "header_flags": {
            "machine": int(pe.FILE_HEADER.Machine),
            "characteristics": int(pe.FILE_HEADER.Characteristics),
            "dll_characteristics": int(getattr(pe.OPTIONAL_HEADER, "DllCharacteristics", 0)),
        },
        "import_vocab_size": len(SUSPICIOUS_API_VOCAB),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract PE features from a Windows binary.")
    parser.add_argument("file_path", type=Path, help="Path to the PE file")
    args = parser.parse_args()

    result = extract_pe_features(args.file_path)
    print(json.dumps(result, indent=2))
