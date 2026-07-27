"""Persistence layer for scans, alerts, incidents, watcher config, and telemetry."""

from __future__ import annotations

import asyncio
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from config import Settings

try:
    from motor.motor_asyncio import AsyncIOMotorClient
except ModuleNotFoundError:
    AsyncIOMotorClient = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TelemetryRepository:
    """Store dashboard data in MongoDB when configured, otherwise in a local JSON file."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.use_mongo = bool(settings.mongo_uri.strip()) and AsyncIOMotorClient is not None
        self._mongo_client: AsyncIOMotorClient | None = None
        self._db = None
        self._path = settings.telemetry_store_path
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        if self.use_mongo:
            self._mongo_client = AsyncIOMotorClient(self.settings.mongo_uri)
            self._db = self._mongo_client[self.settings.mongo_db]
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._path.write_text(
                json.dumps(
                    {
                        "scans": [],
                        "scan_results": [],
                        "label_actions": [],
                        "model_metadata": [],
                        "alerts": [],
                        "incidents": [],
                        "watch_folders": [],
                        "telemetry_events": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

    async def close(self) -> None:
        if self._mongo_client is not None:
            self._mongo_client.close()

    async def _read_local(self) -> dict[str, Any]:
        async with self._lock:
            if not self._path.exists():
                return {
                    "scans": [],
                    "scan_results": [],
                    "label_actions": [],
                    "model_metadata": [],
                    "alerts": [],
                    "incidents": [],
                    "watch_folders": [],
                    "telemetry_events": [],
                }
            return json.loads(self._path.read_text(encoding="utf-8"))

    async def _write_local(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    async def _insert(self, collection: str, document: dict[str, Any]) -> None:
        if self.use_mongo:
            await self._db[collection].insert_one(dict(document))
            return
        payload = await self._read_local()
        payload[collection].append(document)
        await self._write_local(payload)

    async def _replace_watch_folders(self, folders: list[dict[str, Any]]) -> None:
        if self.use_mongo:
            await self._db["watch_folders"].delete_many({})
            if folders:
                await self._db["watch_folders"].insert_many(folders)
            return
        payload = await self._read_local()
        payload["watch_folders"] = folders
        await self._write_local(payload)

    async def _get_collection(self, collection: str) -> list[dict[str, Any]]:
        if self.use_mongo:
            docs = await self._db[collection].find().to_list(length=5000)
            return [self._normalize_mongo_doc(doc) for doc in docs]
        payload = await self._read_local()
        return payload.get(collection, [])

    def _normalize_mongo_doc(self, doc: dict[str, Any] | None) -> dict[str, Any] | None:
        if not doc:
            return doc
        if "_id" in doc:
            doc = {**doc, "_id": str(doc["_id"])}
        return doc

    async def insert_scan(self, scan: dict[str, Any]) -> None:
        await self._insert("scans", scan)

    async def insert_scan_result(self, result: dict[str, Any]) -> None:
        if self.use_mongo:
            await self._db["scan_results"].delete_many({"sha256": result.get("sha256")})
            await self._db["scan_results"].insert_one(dict(result))
            return
        payload = await self._read_local()
        results = [
            item
            for item in payload.get("scan_results", [])
            if item.get("sha256") != result.get("sha256")
        ]
        results.append(result)
        payload["scan_results"] = results
        await self._write_local(payload)

    async def list_scans(self, limit: int = 50) -> list[dict[str, Any]]:
        scans = await self._get_collection("scans")
        return sorted(scans, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    async def find_scan(self, sha256: str) -> dict[str, Any] | None:
        scans = await self._get_collection("scans")
        for scan in reversed(scans):
            if scan.get("sha256") == sha256:
                return scan
        return None

    async def find_scan_result(self, sha256: str) -> dict[str, Any] | None:
        if self.use_mongo:
            doc = await self._db["scan_results"].find_one({"sha256": sha256})
            return self._normalize_mongo_doc(doc)
        results = await self._get_collection("scan_results")
        for item in reversed(results):
            if item.get("sha256") == sha256:
                return item
        return None

    async def insert_label_action(self, action: dict[str, Any]) -> None:
        await self._insert("label_actions", action)

    async def list_label_actions(self, limit: int = 50) -> list[dict[str, Any]]:
        actions = await self._get_collection("label_actions")
        return sorted(
            actions, key=lambda item: item.get("created_at", ""), reverse=True
        )[:limit]

    async def insert_model_metadata(self, metadata: dict[str, Any]) -> None:
        await self._insert("model_metadata", metadata)

    async def list_model_metadata(self, limit: int = 50) -> list[dict[str, Any]]:
        metadata = await self._get_collection("model_metadata")
        return sorted(
            metadata, key=lambda item: item.get("created_at", ""), reverse=True
        )[:limit]

    async def insert_telemetry_event(self, event: dict[str, Any]) -> None:
        await self._insert("telemetry_events", event)

    async def list_telemetry_events(
        self,
        limit: int = 100,
        event_type: str | None = None,
    ) -> list[dict[str, Any]]:
        events = await self._get_collection("telemetry_events")
        if event_type:
            events = [event for event in events if event.get("event_type") == event_type]
        return sorted(events, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    async def insert_alert(self, alert: dict[str, Any]) -> None:
        if await self._is_duplicate_alert(alert):
            return
        await self._insert("alerts", alert)
        await self.upsert_incident_from_alert(alert)

    def _alert_signature(self, alert: dict[str, Any]) -> tuple[str, str, str]:
        return (
            str(alert.get("kind", "")),
            str(alert.get("sha256") or alert.get("filename") or ""),
            str(alert.get("title", "")),
        )

    async def _is_duplicate_alert(
        self, alert: dict[str, Any], window_seconds: int = 120
    ) -> bool:
        signature = self._alert_signature(alert)
        if not any(signature):
            return False
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
        cutoff_iso = cutoff.isoformat()

        if self.use_mongo:
            query = {
                "kind": signature[0],
                "title": signature[2],
            }
            if signature[1]:
                query["$or"] = [{"sha256": signature[1]}, {"filename": signature[1]}]
            query["created_at"] = {"$gte": cutoff_iso}
            existing = await self._db["alerts"].find_one(
                query, sort=[("created_at", -1)]
            )
            return existing is not None

        alerts = await self._get_collection("alerts")
        for existing in reversed(alerts):
            if self._alert_signature(existing) != signature:
                continue
            created_at = existing.get("created_at")
            if not created_at:
                continue
            try:
                created_dt = datetime.fromisoformat(created_at)
            except ValueError:
                continue
            if created_dt >= cutoff:
                return True
        return False

    async def list_alerts(self, limit: int = 50) -> list[dict[str, Any]]:
        alerts = await self._get_collection("alerts")
        return sorted(alerts, key=lambda item: item.get("created_at", ""), reverse=True)[:limit]

    async def upsert_incident_from_alert(self, alert: dict[str, Any]) -> None:
        key = alert.get("sha256") or alert.get("filename") or alert.get("title")
        incidents = await self._get_collection("incidents")
        existing = next((item for item in incidents if item.get("entity_key") == key), None)
        if existing:
            existing["last_seen"] = alert.get("created_at")
            existing["alert_count"] = int(existing.get("alert_count", 1)) + 1
            existing["severity"] = alert.get("severity")
            existing["summary"] = alert.get("summary")
        else:
            incidents.append(
                {
                    "id": alert.get("id"),
                    "entity_key": key,
                    "title": alert.get("title"),
                    "severity": alert.get("severity"),
                    "summary": alert.get("summary"),
                    "alert_count": 1,
                    "sha256": alert.get("sha256"),
                    "filename": alert.get("filename"),
                    "first_seen": alert.get("created_at"),
                    "last_seen": alert.get("created_at"),
                }
            )

        if self.use_mongo:
            await self._db["incidents"].delete_many({})
            if incidents:
                await self._db["incidents"].insert_many(incidents)
            return

        payload = await self._read_local()
        payload["incidents"] = incidents
        await self._write_local(payload)

    async def list_incidents(self, limit: int = 50) -> list[dict[str, Any]]:
        incidents = await self._get_collection("incidents")
        return sorted(incidents, key=lambda item: item.get("last_seen", ""), reverse=True)[:limit]

    async def list_watch_folders(self) -> list[dict[str, Any]]:
        folders = await self._get_collection("watch_folders")
        return sorted(folders, key=lambda item: item.get("path", ""))

    async def upsert_watch_folder(self, folder: dict[str, Any]) -> dict[str, Any]:
        folders = await self.list_watch_folders()
        updated = False
        for current in folders:
            if current.get("path", "").lower() == folder.get("path", "").lower():
                current.update(folder)
                updated = True
                break
        if not updated:
            folders.append(folder)
        await self._replace_watch_folders(folders)
        return folder

    async def remove_watch_folder(self, path: str) -> None:
        folders = await self.list_watch_folders()
        folders = [item for item in folders if item.get("path", "").lower() != path.lower()]
        await self._replace_watch_folders(folders)

    async def analytics_snapshot(self) -> dict[str, Any]:
        scans = await self._get_collection("scans")
        alerts = await self._get_collection("alerts")
        telemetry = await self._get_collection("telemetry_events")
        watch_folders = await self._get_collection("watch_folders")
        incidents = await self._get_collection("incidents")

        family_counter = Counter(scan.get("prediction", "Unknown") for scan in scans)
        severity_counter = Counter(alert.get("severity", "low") for alert in alerts)
        source_counter = Counter(scan.get("source", "manual_upload") for scan in scans)
        timeline_counter: dict[str, int] = defaultdict(int)
        confidence_bands = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        yara_counter = Counter()

        for scan in scans:
            created_at = scan.get("created_at", "")
            bucket = created_at[:13] if created_at else "unknown"
            timeline_counter[bucket] += 1
            confidence = int(float(scan.get("confidence", 0.0)) * 100)
            if confidence <= 20:
                confidence_bands["0-20"] += 1
            elif confidence <= 40:
                confidence_bands["21-40"] += 1
            elif confidence <= 60:
                confidence_bands["41-60"] += 1
            elif confidence <= 80:
                confidence_bands["61-80"] += 1
            else:
                confidence_bands["81-100"] += 1
            for match in scan.get("yara_matches", []):
                yara_counter[match.get("rule", "unknown")] += 1

        network_events = [event for event in telemetry if event.get("event_type") == "network_connection"]
        watch_activity = Counter(event.get("watch_path", "unknown") for event in telemetry if event.get("watch_path"))

        return {
            "overview": {
                "scan_count": len(scans),
                "alert_count": len(alerts),
                "incident_count": len(incidents),
                "watch_folder_count": len(watch_folders),
                "avg_scan_time_ms": round(
                    sum(int(scan.get("scan_time_ms", 0)) for scan in scans) / max(len(scans), 1),
                    2,
                ),
                "network_event_count": len(network_events),
            },
            "family_distribution": [
                {"family": family, "count": count} for family, count in family_counter.most_common(10)
            ],
            "severity_distribution": [
                {"severity": severity, "count": count}
                for severity, count in severity_counter.items()
            ],
            "source_breakdown": [
                {"source": source, "count": count} for source, count in source_counter.items()
            ],
            "timeline": [
                {"bucket": bucket, "count": count}
                for bucket, count in sorted(timeline_counter.items())[-12:]
            ],
            "confidence_bands": [
                {"band": band, "count": count} for band, count in confidence_bands.items()
            ],
            "yara_hits": [{"rule": rule, "count": count} for rule, count in yara_counter.most_common(8)],
            "watch_activity": [
                {"watch_path": watch_path, "count": count}
                for watch_path, count in watch_activity.most_common(8)
            ],
        }
