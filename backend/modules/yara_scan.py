"""YARA rule compilation and scanning helpers for static signature checks."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any

import yara

from config import get_settings

_YARA_RULES: yara.Rules | None = None
_YARA_LOCK = Lock()
_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="aegis-yara")


def _compile_rules() -> yara.Rules:
    global _YARA_RULES
    if _YARA_RULES is None:
        with _YARA_LOCK:
            if _YARA_RULES is None:
                rule_sources = {
                    rule_file.stem: str(rule_file)
                    for rule_file in sorted(get_settings().rules_dir.glob("*.yar"))
                }
                if not rule_sources:
                    raise FileNotFoundError(
                        "No YARA rules found in backend/rules. Add .yar files before scanning."
                    )
                _YARA_RULES = yara.compile(filepaths=rule_sources)
    return _YARA_RULES


def scan_file_with_yara(file_path: Path) -> dict[str, Any]:
    """Run YARA matching against a file and return structured matches."""

    rules = _compile_rules()
    matches = rules.match(str(Path(file_path)))

    structured_matches: list[dict[str, Any]] = []
    confidence = 0.0

    for match in matches:
        offsets: list[int] = []
        matched_strings: list[str] = []
        for string_match in match.strings:
            matched_strings.append(str(string_match.identifier))
            for instance in string_match.instances:
                offsets.append(int(instance.offset))

        structured_matches.append(
            {
                "rule": match.rule,
                "offsets": offsets,
                "matched_strings": matched_strings,
                "tags": match.tags,
            }
        )

        if "family" in match.tags or "malware" in match.tags:
            confidence = max(confidence, 0.9)
        elif "packer" in match.tags:
            confidence = max(confidence, 0.5)
        else:
            confidence = max(confidence, 0.7)

    return {"matches": structured_matches, "yara_confidence": confidence}


async def scan_file_with_yara_async(file_path: Path) -> dict[str, Any]:
    """Run YARA scanning in a thread so API inference can continue in parallel."""

    import asyncio

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_EXECUTOR, scan_file_with_yara, file_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run YARA scan on a file.")
    parser.add_argument("file_path", type=Path, help="Path to the binary file")
    args = parser.parse_args()

    result = scan_file_with_yara(args.file_path)
    print(json.dumps(result, indent=2))
