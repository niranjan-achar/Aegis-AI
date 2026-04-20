"""FastAPI orchestrator for Aegis-AI malware scanning and active learning."""

from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import mlflow
from celery import Celery
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from redis.asyncio import Redis, from_url

from config import get_settings
from constants import CLASS_LABELS
from modules.binary_image import binary_file_to_image
from modules.inference import run_inference
from modules.ingestion import ingest_upload
from modules.ngram import extract_ngram_features
from modules.pe_extractor import extract_pe_features
from modules.xai import generate_gradcam_explanation
from modules.yara_scan import scan_file_with_yara_async


settings = get_settings()
mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

redis_client: Redis | None = None
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_client = from_url(settings.redis_url, decode_responses=True)
    try:
        yield
    finally:
        if redis_client:
            await redis_client.aclose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _get_redis() -> Redis:
    if redis_client is None:
        raise HTTPException(status_code=503, detail="Redis client not initialised.")
    return redis_client


def _queue_key(sha256: str) -> str:
    return f"aegis:queue:item:{sha256}"


async def _add_to_learning_queue(payload: dict[str, Any]) -> None:
    client = await _get_redis()
    sha256 = payload["sha256"]
    await client.hset("aegis:queue:index", sha256, _queue_key(sha256))
    await client.set(_queue_key(sha256), json.dumps(payload))


def _threat_score(confidence: float, yara_confidence: float, prediction: str) -> int:
    family_multiplier = 0.35 if prediction == "Benign" else 1.0
    score = ((confidence * 0.75) + (yara_confidence * 0.25)) * 100 * family_multiplier
    return max(0, min(100, int(round(score))))


@app.get("/api/health")
async def health() -> dict[str, Any]:
    client = await _get_redis()
    redis_ok = await client.ping()
    return {"status": "ok", "redis": bool(redis_ok), "environment": settings.env}


@app.post("/api/scan")
async def scan_file(file: UploadFile = File(...)) -> dict[str, Any]:
    start = time.perf_counter()
    client = await _get_redis()
    ingestion_result = await ingest_upload(file, client)
    if ingestion_result["cache_hit"]:
        return ingestion_result["cached_result"]

    sha256 = ingestion_result["sha256"]
    file_path = Path(ingestion_result["file_path"])

    image_task = asyncio.to_thread(binary_file_to_image, file_path, sha256)
    pe_task = asyncio.to_thread(extract_pe_features, file_path)
    ngram_task = asyncio.to_thread(extract_ngram_features, file_path)
    yara_task = asyncio.create_task(scan_file_with_yara_async(file_path))

    image_result, pe_result, ngram_result = await asyncio.gather(image_task, pe_task, ngram_task)
    combined_features = pe_result["feature_vector"] + ngram_result["ngram_vector"]
    inference_result = await asyncio.to_thread(run_inference, Path(image_result["image_path"]), combined_features)
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
    threat_score = _threat_score(confidence, yara_confidence, inference_result["prediction"])
    flagged_for_learning = confidence < 0.70

    response = {
        "sha256": sha256,
        "filename": file.filename,
        "prediction": inference_result["prediction"],
        "confidence": confidence,
        "threat_score": threat_score,
        "top3": inference_result["top3"],
        "yara_matches": yara_result["matches"],
        "yara_confidence": yara_confidence,
        "top_offsets": xai_result["top_offsets"],
        "heatmap_b64": xai_result["heatmap_b64"],
        "image_b64": image_result["image_b64"],
        "pe_features": pe_result,
        "flagged_for_learning": flagged_for_learning,
        "scan_time_ms": int((time.perf_counter() - start) * 1000),
    }

    await client.setex(f"aegis:scan:{sha256}", settings.cache_ttl_seconds, json.dumps(response))

    if flagged_for_learning:
        queue_item = QueueItem(
            sha256=sha256,
            filename=file.filename or f"{sha256}.bin",
            prediction=inference_result["prediction"],
            confidence=confidence,
            queued_at=time.time(),
            yara_confidence=yara_confidence,
            image_b64=image_result["image_b64"],
            heatmap_b64=xai_result["heatmap_b64"],
            top3=inference_result["top3"],
        ).model_dump()
        await _add_to_learning_queue(queue_item)
    elif yara_confidence > 0.9:
        celery_app.send_task(
            "workers.ewc_worker.retrain_sample",
            kwargs={"file_path": str(file_path), "sha256": sha256, "label": inference_result["prediction"]},
        )

    return response


@app.get("/api/evolution")
async def get_evolution_history() -> dict[str, Any]:
    client = mlflow.tracking.MlflowClient()
    experiments = client.search_experiments()
    experiment_ids = [exp.experiment_id for exp in experiments] or ["0"]
    runs = client.search_runs(
        experiment_ids=experiment_ids,
        order_by=["attributes.start_time DESC"],
        max_results=50,
    )
    history = []
    for run in runs:
        history.append(
            {
                "run_id": run.info.run_id,
                "status": run.info.status,
                "start_time": run.info.start_time,
                "version": run.data.tags.get("model_version", "n/a"),
                "trigger": run.data.tags.get("trigger", "manual"),
                "accuracy": float(run.data.metrics.get("mean_accuracy", 0.0)),
                "ewc_loss": float(run.data.metrics.get("ewc_loss", 0.0)),
                "families": json.loads(run.data.tags.get("families", "[]")),
                "metrics": {key: float(value) for key, value in run.data.metrics.items()},
            }
        )
    return {"runs": history}


@app.get("/api/queue")
async def get_learning_queue() -> dict[str, Any]:
    client = await _get_redis()
    index = await client.hgetall("aegis:queue:index")
    items = []
    for _, item_key in index.items():
        raw = await client.get(item_key)
        if raw:
            items.append(json.loads(raw))
    items.sort(key=lambda item: item["queued_at"], reverse=True)
    return {"items": items}


@app.post("/api/label")
async def confirm_label(payload: LabelRequest) -> dict[str, Any]:
    if payload.label not in CLASS_LABELS:
        raise HTTPException(status_code=400, detail="Unknown class label.")

    client = await _get_redis()
    item_key = await client.hget("aegis:queue:index", payload.sha256)
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


@app.websocket("/ws/training")
async def training_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    client = await _get_redis()
    pubsub = client.pubsub()
    await pubsub.subscribe("training_progress")

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
