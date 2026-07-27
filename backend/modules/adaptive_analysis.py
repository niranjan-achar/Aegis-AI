"""Heuristics to flag adaptive/self-evolving malware indicators from static signals."""

from __future__ import annotations

from typing import Any


ANTI_DEBUG_APIS = {
    "IsDebuggerPresent",
    "CheckRemoteDebuggerPresent",
    "NtQueryInformationProcess",
    "OutputDebugStringA",
    "OutputDebugStringW",
}

TIMING_APIS = {
    "GetTickCount",
    "QueryPerformanceCounter",
    "Sleep",
    "NtDelayExecution",
}

INJECTION_APIS = {
    "CreateRemoteThread",
    "CreateRemoteThreadEx",
    "VirtualAllocEx",
    "WriteProcessMemory",
    "OpenProcess",
}

ENV_APIS = {
    "GetSystemMetrics",
    "GetComputerNameA",
    "GetComputerNameW",
    "GetUserNameA",
    "GetUserNameW",
    "GetVersionExA",
    "GetVersionExW",
}


def _flatten_imports(imports_by_dll: dict[str, list[str]]) -> set[str]:
    names: set[str] = set()
    for dll_imports in imports_by_dll.values():
        for name in dll_imports:
            names.add(name)
    return names


def analyze_adaptive_indicators(
    pe_result: dict[str, Any],
    yara_result: dict[str, Any],
) -> dict[str, Any]:
    sections = pe_result.get("sections", [])
    imports_by_dll = pe_result.get("imports", {}) or {}
    imported_names = _flatten_imports(imports_by_dll)
    yara_matches = yara_result.get("matches", [])

    high_entropy_sections = [
        section for section in sections if float(section.get("entropy", 0.0)) >= 7.2
    ]
    packed_section_names = [
        section.get("name", "").lower()
        for section in sections
        if section.get("name", "").lower().startswith("upx")
    ]
    packer_rule_hits = [
        match.get("rule")
        for match in yara_matches
        if "packer" in (match.get("tags") or [])
        or "upx" in str(match.get("rule", "")).lower()
    ]

    anti_debug_hits = sorted(ANTI_DEBUG_APIS.intersection(imported_names))
    timing_hits = sorted(TIMING_APIS.intersection(imported_names))
    injection_hits = sorted(INJECTION_APIS.intersection(imported_names))
    env_check_hits = sorted(ENV_APIS.intersection(imported_names))

    score = 0
    score += 20 if high_entropy_sections else 0
    score += 15 if packed_section_names else 0
    score += 20 if packer_rule_hits else 0
    score += 15 if anti_debug_hits else 0
    score += 10 if timing_hits else 0
    score += 10 if injection_hits else 0
    score += 10 if env_check_hits else 0

    indicators = []
    if high_entropy_sections:
        indicators.append("high_entropy_sections")
    if packed_section_names or packer_rule_hits:
        indicators.append("packer_or_packed")
    if anti_debug_hits:
        indicators.append("anti_debug_checks")
    if timing_hits:
        indicators.append("timing_evasion")
    if injection_hits:
        indicators.append("process_injection")
    if env_check_hits:
        indicators.append("environment_fingerprinting")

    return {
        "adaptive_score": min(score, 100),
        "indicators": indicators,
        "details": {
            "high_entropy_sections": [section.get("name") for section in high_entropy_sections],
            "packer_rule_hits": packer_rule_hits,
            "anti_debug_apis": anti_debug_hits,
            "timing_apis": timing_hits,
            "injection_apis": injection_hits,
            "environment_apis": env_check_hits,
        },
    }