"""FastAPI orchestrator for scanning, telemetry, alerts, and dashboard APIs."""

from __future__ import annotations

import asyncio
import hashlib
import json
import platform
import shutil
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import psutil
except ModuleNotFoundError:
    psutil = None

from celery import Celery
from config import get_settings
from constants import CLASS_LABELS
from fastapi import (
    FastAPI,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from modules.binary_image import binary_file_to_image
from modules.inference import run_inference
from modules.ingestion import MAX_UPLOAD_SIZE, ingest_upload
from modules.ngram import extract_ngram_features
from modules.pe_extractor import extract_pe_features
from modules.xai import generate_gradcam_explanation
from modules.yara_scan import scan_file_with_yara_async
from pydantic import BaseModel, Field
from redis.asyncio import Redis, from_url
from telemetry.hub import LiveEventHub
from telemetry.monitors import NetworkMonitor, WatchFolderManager
from telemetry.risk_engine import (
    build_file_event_alert,
    build_network_alert,
    build_scan_alert,
)
from telemetry.store import TelemetryRepository, utc_now

try:
    import mlflow
except ModuleNotFoundError:
    mlflow = None


settings = get_settings()
if mlflow is not None:
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

redis_client: Redis | None = None
repository: TelemetryRepository | None = None
watch_manager: WatchFolderManager | None = None
network_monitor: NetworkMonitor | None = None
network_monitor_task: asyncio.Task | None = None
event_hub = LiveEventHub()

celery_app = Celery(
    "aegis_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)


class LabelRequest(BaseModel):
    sha256: str
    label: str = Field(..., description="Confirmed malware family or Benign label")


class QueueItem(BaseModel):
    sha256: str
    filename: str
    prediction: str
    confidence: float
    queued_at: float
    yara_confidence: float
    image_b64: str | None = None
    heatmap_b64: str | None = None
    top3: list[dict[str, Any]] = Field(default_factory=list)


class WatchFolderRequest(BaseModel):
    path: str
    recursive: bool = True
    extensions: list[str] | None = None


def _queue_key(sha256: str) -> str:
    return f"aegis:queue:item:{sha256}"


def _threat_score(confidence: float, yara_confidence: float, prediction: str) -> int:
    family_multiplier = 0.35 if prediction == "Benign" else 1.0
    score = ((confidence * 0.75) + (yara_confidence * 0.25)) * 100 * family_multiplier
    return max(0, min(100, int(round(score))))


def _hash_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_record(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "created_at": response["created_at"],
        "sha256": response["sha256"],
        "filename": response["filename"],
        "prediction": response["prediction"],
        "confidence": response["confidence"],
        "threat_score": response["threat_score"],
        "top3": response["top3"],
        "yara_matches": response["yara_matches"],
        "yara_confidence": response["yara_confidence"],
        "flagged_for_learning": response["flagged_for_learning"],
        "scan_time_ms": response["scan_time_ms"],
        "source": response.get("source", "manual_upload"),
        "watch_path": response.get("watch_path"),
        "cache_hit": response.get("cache_hit", False),
    }


async def _get_redis() -> Redis:
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis client not initialised.")
    return redis_client


async def _redis_ping() -> bool:
    if redis_client is None:
        return False
    try:
        return bool(await redis_client.ping())
    except Exception:
        return False


async def _get_repository() -> TelemetryRepository:
    if repository is None:
        raise HTTPException(
            status_code=503, detail="Telemetry repository not initialised."
        )
    return repository


async def _broadcast(event_type: str, payload: dict[str, Any]) -> None:
    await event_hub.broadcast("telemetry", {"type": event_type, "payload": payload})


async def _add_to_learning_queue(payload: dict[str, Any]) -> None:
    if not await _redis_ping():
        return
    client = await _get_redis()
    sha256 = payload["sha256"]
    try:
        await client.hset("aegis:queue:index", sha256, _queue_key(sha256))
        await client.set(_queue_key(sha256), json.dumps(payload))
    except Exception:
        return


async def _persist_alert(alert: dict[str, Any] | None) -> None:
    if alert is None:
        return
    repo = await _get_repository()
    if not alert.get("created_at"):
        alert["created_at"] = utc_now()
    await repo.insert_alert(alert)
    await _broadcast("alert_created", alert)


def _default_watch_folders() -> list[dict[str, Any]]:
    folders = []
    for path in (Path.home() / "Downloads", Path.home() / "Desktop"):
        if path.exists():
            folders.append(
                {
                    "id": str(uuid4()),
                    "path": str(path),
                    "recursive": True,
                    "extensions": settings.watch_extension_list(),
                    "created_at": utc_now(),
                }
            )
    return folders


async def _ensure_default_watch_folders() -> None:
    repo = await _get_repository()
    current = await repo.list_watch_folders()
    if current:
        return
    for folder in _default_watch_folders():
        await repo.upsert_watch_folder(folder)


async def _persist_scan_response(response: dict[str, Any]) -> None:
    repo = await _get_repository()
    scan = _scan_record(response)
    await repo.insert_scan(scan)
    await _broadcast("scan_completed", scan)
    await _persist_alert(build_scan_alert(scan))


async def _run_scan_pipeline(
    file_path: Path,
    filename: str,
    source: str,
    watch_path: str | None = None,
) -> dict[str, Any]:
    client = redis_client if await _redis_ping() else None
    sha256 = await asyncio.to_thread(_hash_file, file_path)
    cache_key = f"aegis:scan:{sha256}"
    cached = None
    if client is not None:
        try:
            cached = await client.get(cache_key)
        except Exception:
            cached = None

    if cached:
        response = json.loads(cached)
    else:
        started = time.perf_counter()
        image_task = asyncio.to_thread(binary_file_to_image, file_path, sha256)
        pe_task = asyncio.to_thread(extract_pe_features, file_path)
        ngram_task = asyncio.to_thread(extract_ngram_features, file_path)
        yara_task = asyncio.create_task(scan_file_with_yara_async(file_path))

        image_result, pe_result, ngram_result = await asyncio.gather(
            image_task, pe_task, ngram_task
        )
        combined_features = pe_result["feature_vector"] + ngram_result["ngram_vector"]
        inference_result = await asyncio.to_thread(
            run_inference, Path(image_result["image_path"]), combined_features
        )
        yara_result = await yara_task

        predicted_index = CLASS_LABELS.index(inference_result["prediction"])
        xai_result = await asyncio.to_thread(
            generate_gradcam_explanation,
            Path(image_result["image_path"]),
            sha256,
            file_path,
            predicted_index,
        )

        confidence = float(inference_result["confidence"])
        yara_confidence = float(yara_result["yara_confidence"])
        response = {
            "sha256": sha256,
            "filename": filename,
            "prediction": inference_result["prediction"],
            "confidence": confidence,
            "threat_score": _threat_score(
                confidence, yara_confidence, inference_result["prediction"]
            ),
            "top3": inference_result["top3"],
            "yara_matches": yara_result["matches"],
            "yara_confidence": yara_confidence,
            "top_offsets": xai_result["top_offsets"],
            "heatmap_b64": xai_result["heatmap_b64"],
            "image_b64": image_result["image_b64"],
            "pe_features": pe_result,
            "flagged_for_learning": confidence < 0.70,
            "scan_time_ms": int((time.perf_counter() - started) * 1000),
        }
        if client is not None:
            try:
                await client.setex(
                    cache_key, settings.cache_ttl_seconds, json.dumps(response)
                )
            except Exception:
                pass

    response = {
        **response,
        "sha256": sha256,
        "filename": filename,
        "source": source,
        "watch_path": watch_path,
        "created_at": utc_now(),
        "cache_hit": bool(cached),
    }

    await _persist_scan_response(response)

    if response["flagged_for_learning"]:
        queue_item = QueueItem(
            sha256=sha256,
            filename=filename,
            prediction=response["prediction"],
            confidence=response["confidence"],
            queued_at=time.time(),
            yara_confidence=response["yara_confidence"],
            image_b64=response.get("image_b64"),
            heatmap_b64=response.get("heatmap_b64"),
            top3=response.get("top3", []),
        ).model_dump()
        await _add_to_learning_queue(queue_item)

    return response


async def _handle_watched_file(path: Path, watch_config: dict[str, Any]) -> None:
    event = {
        "id": str(uuid4()),
        "event_type": "file_created",
        "created_at": utc_now(),
        "path": str(path),
        "filename": path.name,
        "extension": path.suffix.lower(),
        "watch_path": watch_config["path"],
        "recursive": bool(watch_config.get("recursive", True)),
    }
    repo = await _get_repository()
    await repo.insert_telemetry_event(event)
    await _broadcast("file_created", event)
    await _persist_alert(build_file_event_alert(event))

    if path.suffix.lower() in {".exe", ".dll"}:
        try:
            if path.exists() and path.stat().st_size <= MAX_UPLOAD_SIZE:
                await _run_scan_pipeline(
                    path, path.name, "watcher", watch_config["path"]
                )
        except Exception as exc:
            failure_event = {
                "id": str(uuid4()),
                "event_type": "watcher_scan_failed",
                "created_at": utc_now(),
                "path": str(path),
                "error": str(exc),
                "watch_path": watch_config["path"],
            }
            await repo.insert_telemetry_event(failure_event)
            await _broadcast("watcher_scan_failed", failure_event)


async def _handle_network_event(event: dict[str, Any]) -> None:
    repo = await _get_repository()
    await repo.insert_telemetry_event(event)
    await _broadcast("network_connection", event)
    await _persist_alert(build_network_alert(event))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global network_monitor
    global network_monitor_task
    global redis_client
    global repository
    global watch_manager

    redis_client = from_url(settings.redis_url, decode_responses=True)
    repository = TelemetryRepository(settings)
    await repository.connect()
    await _ensure_default_watch_folders()

    watch_manager = WatchFolderManager(settings, _handle_watched_file)
    await watch_manager.start()
    await watch_manager.sync_folders(await repository.list_watch_folders())

    if psutil is not None:
        network_monitor = NetworkMonitor(settings, _handle_network_event)
        network_monitor_task = asyncio.create_task(network_monitor.run())
    else:
        network_monitor = None
        network_monitor_task = None

    try:
        yield
    finally:
        if network_monitor is not None:
            await network_monitor.stop()
        if network_monitor_task is not None:
            network_monitor_task.cancel()
            with suppress(asyncio.CancelledError):
                await network_monitor_task
        if watch_manager is not None:
            await watch_manager.stop()
        if repository is not None:
            await repository.close()
        if redis_client is not None:
            await redis_client.aclose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    repo = await _get_repository()
    redis_ok = await _redis_ping()
    watch_folders = await repo.list_watch_folders()
    return {
        "status": "ok",
        "redis": bool(redis_ok),
        "mongo_enabled": repo.use_mongo,
        "mlflow_enabled": mlflow is not None,
        "psutil_enabled": psutil is not None,
        "watch_folder_count": len(watch_folders),
        "environment": settings.env,
    }


@app.post("/api/scan")
async def scan_file(file: UploadFile = File(...)) -> dict[str, Any]:
    client = redis_client if await _redis_ping() else None
    ingestion_result = await ingest_upload(file, client)
    if ingestion_result["cache_hit"]:
        cached = {
            **ingestion_result["cached_result"],
            "filename": file.filename,
            "source": "manual_upload",
            "created_at": utc_now(),
            "cache_hit": True,
        }
        await _persist_scan_response(cached)
        return cached

    file_path = Path(ingestion_result["file_path"])
    return await _run_scan_pipeline(
        file_path, file.filename or file_path.name, "manual_upload"
    )


@app.get("/api/scans")
async def list_scans(limit: int = Query(default=25, ge=1, le=200)) -> dict[str, Any]:
    repo = await _get_repository()
    return {"items": await repo.list_scans(limit)}


@app.get("/api/evolution")
async def get_evolution_history() -> dict[str, Any]:
    if mlflow is None:
        return {
            "runs": [],
            "tracking": "unavailable",
            "message": "MLflow is not installed in the current environment.",
        }
    try:
        client = mlflow.tracking.MlflowClient()
        try:
            experiments = client.search_experiments()
            experiment_ids = [exp.experiment_id for exp in experiments] or ["0"]
        except Exception:
            experiment_ids = ["0"]

        try:
            runs = client.search_runs(
                experiment_ids=experiment_ids,
                order_by=["attributes.start_time DESC"],
                max_results=50,
            )
        except Exception:
            return {
                "runs": [],
                "tracking": "unavailable",
                "message": "MLflow tracking data is incompatible with the installed MLflow version.",
            }

        history = []
        for run in runs:
            families_tag = run.data.tags.get("families", "[]")
            try:
                families = json.loads(families_tag)
            except Exception:
                families = []
            history.append(
                {
                    "run_id": run.info.run_id,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "version": run.data.tags.get("model_version", "n/a"),
                    "trigger": run.data.tags.get("trigger", "manual"),
                    "accuracy": float(run.data.metrics.get("mean_accuracy", 0.0)),
                    "ewc_loss": float(run.data.metrics.get("ewc_loss", 0.0)),
                    "families": families,
                    "metrics": {
                        key: float(value) for key, value in run.data.metrics.items()
                    },
                }
            )
        return {"runs": history, "tracking": "available"}
    except Exception as exc:
        return {
            "runs": [],
            "tracking": "unavailable",
            "message": f"MLflow history is unavailable: {exc}",
        }


@app.get("/api/queue")
async def get_learning_queue() -> dict[str, Any]:
    if not await _redis_ping():
        return {"items": []}
    client = await _get_redis()
    try:
        index = await client.hgetall("aegis:queue:index")
    except Exception:
        return {"items": []}
    items = []
    for _, item_key in index.items():
        try:
            raw = await client.get(item_key)
        except Exception:
            raw = None
        if raw:
            items.append(json.loads(raw))
    items.sort(key=lambda item: item["queued_at"], reverse=True)
    return {"items": items}


@app.post("/api/label")
async def confirm_label(payload: LabelRequest) -> dict[str, Any]:
    if payload.label not in CLASS_LABELS:
        raise HTTPException(status_code=400, detail="Unknown class label.")

    if not await _redis_ping():
        raise HTTPException(
            status_code=503,
            detail="Redis is unavailable. Queue features require Redis.",
        )
    client = await _get_redis()
    try:
        item_key = await client.hget("aegis:queue:index", payload.sha256)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Queue lookup failed: {exc}"
        ) from exc
    if not item_key:
        raise HTTPException(status_code=404, detail="Queue item not found.")

    item = await client.get(item_key)
    if not item:
        raise HTTPException(status_code=404, detail="Queue payload missing.")
    queue_item = json.loads(item)

    file_path = settings.upload_dir / f"{payload.sha256}.bin"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Source file not found for retraining.")

    task = celery_app.send_task(
        "workers.ewc_worker.retrain_sample",
        kwargs={"file_path": str(file_path), "sha256": payload.sha256, "label": payload.label},
    )
    queue_item["confirmed_label"] = payload.label
    queue_item["task_id"] = task.id
    await client.set(item_key, json.dumps(queue_item))
    return {"queued": True, "task_id": task.id}


@app.get("/api/watchers")
async def list_watchers() -> dict[str, Any]:
    repo = await _get_repository()
    return {"items": await repo.list_watch_folders()}


@app.post("/api/watchers")
async def create_watch_folder(payload: WatchFolderRequest) -> dict[str, Any]:
    repo = await _get_repository()
    folder = {
        "id": str(uuid4()),
        "path": str(Path(payload.path).expanduser().resolve()),
        "recursive": payload.recursive,
        "extensions": payload.extensions or settings.watch_extension_list(),
        "created_at": utc_now(),
    }
    await repo.upsert_watch_folder(folder)
    if watch_manager is not None:
        await watch_manager.add_folder(folder)
    await _broadcast("watch_folder_added", folder)
    return {"item": folder}


@app.delete("/api/watchers")
async def delete_watch_folder(
    path: str = Query(..., description="Absolute folder path")
) -> dict[str, Any]:
    repo = await _get_repository()
    await repo.remove_watch_folder(path)
    if watch_manager is not None:
        await watch_manager.remove_folder(path)
    await _broadcast("watch_folder_removed", {"path": path})
    return {"removed": True}


@app.get("/api/telemetry")
async def list_telemetry(
    limit: int = Query(default=100, ge=1, le=300),
    event_type: str | None = Query(default=None),
) -> dict[str, Any]:
    repo = await _get_repository()
    return {"items": await repo.list_telemetry_events(limit, event_type)}


@app.get("/api/alerts")
async def list_alerts(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    repo = await _get_repository()
    return {"items": await repo.list_alerts(limit)}


@app.get("/api/incidents")
async def list_incidents(
    limit: int = Query(default=50, ge=1, le=200)
) -> dict[str, Any]:
    repo = await _get_repository()
    return {"items": await repo.list_incidents(limit)}


@app.get("/api/analytics")
async def analytics() -> dict[str, Any]:
    repo = await _get_repository()
    return await repo.analytics_snapshot()


@app.get("/api/network")
async def network_snapshot(
    limit: int = Query(default=50, ge=1, le=300)
) -> dict[str, Any]:
    repo = await _get_repository()
    events = await repo.list_telemetry_events(
        limit=limit, event_type="network_connection"
    )
    processes: dict[str, int] = {}
    ports: dict[str, int] = {}
    for event in events:
        process_name = event.get("process_name", "unknown")
        processes[process_name] = processes.get(process_name, 0) + 1
        port_key = str(event.get("remote_port", 0))
        ports[port_key] = ports.get(port_key, 0) + 1
    return {
        "connections": events,
        "top_processes": [
            {"process": name, "count": count}
            for name, count in sorted(
                processes.items(), key=lambda item: item[1], reverse=True
            )[:8]
        ],
        "top_ports": [
            {"port": port, "count": count}
            for port, count in sorted(
                ports.items(), key=lambda item: item[1], reverse=True
            )[:8]
        ],
    }


@app.get("/api/system")
async def system_status() -> dict[str, Any]:
    repo = await _get_repository()
    disk_usage = shutil.disk_usage(settings.data_dir.anchor or str(settings.data_dir))
    redis_ok = await _redis_ping()
    runtime = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu_percent": None,
        "memory_percent": None,
        "disk_percent": round((disk_usage.used / disk_usage.total) * 100, 2),
        "boot_time": None,
    }
    if psutil is not None:
        runtime.update(
            {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": round(psutil.virtual_memory().percent, 2),
                "boot_time": datetime.fromtimestamp(
                    psutil.boot_time(), tz=timezone.utc
                ).isoformat(),
            }
        )
    return {
        "services": {
            "backend": "online",
            "redis": "online" if redis_ok else "offline",
            "mongo": "configured" if repo.use_mongo else "fallback_store",
            "watcher": "active" if watch_manager is not None else "inactive",
            "network_monitor": (
                "active" if network_monitor_task is not None else "inactive"
            ),
            "celery": "configured",
            "telemetry_runtime": "configured" if psutil is not None else "limited",
        },
        "runtime": runtime,
        "assets": {
            "onnx_model": (settings.model_dir / "efficientnet_b1.onnx").exists(),
            "onnx_data": (settings.model_dir / "efficientnet_b1.onnx.data").exists(),
            "pytorch_model": (
                settings.model_dir / "efficientnet_b1_pytorch.pth"
            ).exists(),
            "head": (settings.model_dir / "head.pkl").exists(),
            "fisher": (settings.model_dir / "fisher_matrix.pkl").exists(),
            "replay_buffer": (settings.data_dir / "replay_buffer.pkl").exists(),
            "validation_set": (settings.data_dir / "validation_set.pkl").exists(),
        },
        "watch_folders": await repo.list_watch_folders(),
    }


@app.websocket("/ws/telemetry")
async def telemetry_websocket(websocket: WebSocket) -> None:
    await event_hub.connect("telemetry", websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await event_hub.disconnect("telemetry", websocket)


@app.websocket("/ws/training")
async def training_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    if not await _redis_ping():
        await websocket.send_text(
            json.dumps(
                {"event": "training_unavailable", "message": "Redis is offline."}
            )
        )
        await websocket.close()
        return
    client = await _get_redis()
    pubsub = client.pubsub()
    try:
        await pubsub.subscribe("training_progress")
    except Exception:
        await websocket.send_text(
            json.dumps(
                {
                    "event": "training_unavailable",
                    "message": "Redis pub/sub is unavailable.",
                }
            )
        )
        await websocket.close()
        return

    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=2.0)
            if message and message.get("data"):
                await websocket.send_text(str(message["data"]))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe("training_progress")
        await pubsub.aclose()
