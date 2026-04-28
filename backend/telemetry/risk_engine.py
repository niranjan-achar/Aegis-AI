"""Simple correlation and scoring rules for telemetry-driven alerts."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4


TRUSTED_PROCESS_NAMES = {
    "system",
    "svchost.exe",
    "explorer.exe",
    "code.exe",
    "python.exe",
    "powershell.exe",
    "chrome.exe",
    "msedge.exe",
}


def severity_for_score(score: int) -> str:
    if score >= 90:
        return "critical"
    if score >= 75:
        return "high"
    if score >= 55:
        return "medium"
    return "low"


def build_scan_alert(scan: dict[str, Any]) -> dict[str, Any] | None:
    threat_score = int(scan.get("threat_score", 0))
    prediction = scan.get("prediction", "Unknown")
    if threat_score < 55 and prediction == "Benign":
        return None

    reasons = []
    if prediction != "Benign":
        reasons.append(f"Model predicted {prediction}")
    if float(scan.get("yara_confidence", 0.0)) >= 0.5:
        reasons.append("YARA signatures added supporting evidence")
    if bool(scan.get("flagged_for_learning")):
        reasons.append("Confidence fell below the active-learning threshold")

    return {
        "id": str(uuid4()),
        "kind": "scan_alert",
        "severity": severity_for_score(threat_score),
        "risk_score": threat_score,
        "title": f"{prediction} flagged during {scan.get('source', 'scan')}",
        "summary": f"{scan.get('filename', scan.get('sha256', 'sample'))} reached a threat score of {threat_score}.",
        "reasons": reasons or ["Threat score crossed the alert threshold"],
        "sha256": scan.get("sha256"),
        "filename": scan.get("filename"),
        "source": scan.get("source"),
        "watch_path": scan.get("watch_path"),
        "created_at": scan.get("created_at"),
    }


def build_file_event_alert(event: dict[str, Any]) -> dict[str, Any] | None:
    suffix = Path(event.get("path", "")).suffix.lower()
    if suffix not in {".exe", ".dll", ".scr", ".bat", ".ps1", ".cmd", ".com"}:
        return None

    score = 45 if "downloads" in event.get("path", "").lower() else 35
    return {
        "id": str(uuid4()),
        "kind": "watcher_alert",
        "severity": severity_for_score(score),
        "risk_score": score,
        "title": "New executable detected in watched folder",
        "summary": f"{event.get('path')} was created inside a protected directory.",
        "reasons": ["New executable appeared inside a watched path"],
        "sha256": event.get("sha256"),
        "filename": Path(event.get("path", "")).name,
        "source": "watcher",
        "watch_path": event.get("watch_path"),
        "created_at": event.get("created_at"),
    }


def build_network_alert(event: dict[str, Any]) -> dict[str, Any] | None:
    process_name = str(event.get("process_name", "unknown")).lower()
    remote_port = int(event.get("remote_port", 0) or 0)
    if process_name in TRUSTED_PROCESS_NAMES and remote_port in {80, 443, 53}:
        return None

    score = 40
    reasons = ["Process opened a new outbound connection"]
    if remote_port not in {80, 443, 53}:
        score += 20
        reasons.append(f"Connection used uncommon port {remote_port}")
    if process_name not in TRUSTED_PROCESS_NAMES:
        score += 10
        reasons.append(f"Process {process_name or 'unknown'} is not in the trusted baseline")

    return {
        "id": str(uuid4()),
        "kind": "network_alert",
        "severity": severity_for_score(score),
        "risk_score": score,
        "title": "Suspicious outbound connection observed",
        "summary": f"{event.get('process_name', 'Unknown process')} connected to {event.get('remote_ip')}:{remote_port}.",
        "reasons": reasons,
        "sha256": event.get("sha256"),
        "filename": event.get("process_name"),
        "source": "network_monitor",
        "watch_path": None,
        "created_at": event.get("created_at"),
    }
