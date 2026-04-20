"""Celery worker for Elastic Weight Consolidation continual learning."""

from __future__ import annotations

import json
import pickle
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import onnx
import timm
import torch
import torch.nn.functional as F
from celery import Celery
from redis import Redis
from sklearn.metrics import accuracy_score
from torch.utils.data import DataLoader, Dataset

from config import get_settings
from constants import CLASS_LABELS


settings = get_settings()
mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

celery_app = Celery(
    "aegis_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EWC_LAMBDA = 20.0


class ReplayDataset(Dataset):
    """Tiny dataset wrapper for replay and single-sample updates."""

    def __init__(self, samples: list[dict[str, Any]]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        sample = self.samples[index]
        image = torch.tensor(sample["image"], dtype=torch.float32)
        label = torch.tensor(sample["label_index"], dtype=torch.long)
        return image, label


def _redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def _publish(event: dict[str, Any]) -> None:
    client = _redis()
    client.publish("training_progress", json.dumps(event))
    client.close()


def _load_pickle(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Required file missing: {path}")
    with path.open("rb") as handle:
        return pickle.load(handle)


def _load_model() -> torch.nn.Module:
    weights_path = settings.model_dir / "efficientnet_b1_pytorch.pth"
    if not weights_path.exists():
        raise FileNotFoundError(
            "efficientnet_b1_pytorch.pth not found in backend/models. Run the Colab notebook first."
        )
    model = timm.create_model("efficientnet_b1", pretrained=False, num_classes=len(CLASS_LABELS))
    state_dict = torch.load(weights_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    return model


def _preprocess_image(file_path: Path) -> list[Any]:
    from PIL import Image

    image = Image.open(file_path).convert("RGB").resize((224, 224), Image.Resampling.LANCZOS)
    array = np.asarray(image).astype(np.float32) / 255.0
    array = np.transpose(array, (2, 0, 1))
    return array.tolist()


def _ewc_penalty(
    model: torch.nn.Module,
    fisher: dict[str, torch.Tensor],
    reference_params: dict[str, torch.Tensor],
) -> torch.Tensor:
    penalty = torch.zeros(1, device=DEVICE)
    for name, parameter in model.named_parameters():
        if name in fisher and name in reference_params:
            penalty = penalty + (fisher[name] * (parameter - reference_params[name]).pow(2)).sum()
    return penalty


def _evaluate(model: torch.nn.Module, validation_samples: list[dict[str, Any]]) -> dict[str, float]:
    model.eval()
    accuracies: dict[str, float] = {}
    labels = CLASS_LABELS
    for label_name in labels:
        family_samples = [sample for sample in validation_samples if sample["label"] == label_name]
        if not family_samples:
            continue
        predictions = []
        ground_truth = []
        with torch.no_grad():
            for sample in family_samples:
                image = torch.tensor(sample["image"], dtype=torch.float32).unsqueeze(0).to(DEVICE)
                logits = model(image)
                pred = int(torch.argmax(logits, dim=1).item())
                predictions.append(pred)
                ground_truth.append(int(sample["label_index"]))
        accuracies[label_name] = float(accuracy_score(ground_truth, predictions))
    return accuracies


def _update_fisher(model: torch.nn.Module, loader: DataLoader) -> dict[str, torch.Tensor]:
    fisher = {name: torch.zeros_like(param, device=DEVICE) for name, param in model.named_parameters()}
    model.eval()
    for images, labels in loader:
        images = images.to(DEVICE)
        labels = labels.to(DEVICE)
        model.zero_grad(set_to_none=True)
        loss = F.cross_entropy(model(images), labels)
        loss.backward()
        for name, param in model.named_parameters():
            if param.grad is not None:
                fisher[name] += param.grad.detach().pow(2)
    for name in fisher:
        fisher[name] /= max(len(loader), 1)
    return fisher


def _export_onnx(model: torch.nn.Module, destination: Path) -> None:
    class EmbeddingWrapper(torch.nn.Module):
        def __init__(self, inner_model: torch.nn.Module):
            super().__init__()
            self.inner_model = inner_model

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            features = self.inner_model.forward_features(x)
            pooled = self.inner_model.global_pool(features)
            if pooled.ndim > 2:
                pooled = torch.flatten(pooled, 1)
            return pooled

    model.eval()
    export_model = EmbeddingWrapper(model).to(DEVICE)
    dummy = torch.randn(1, 3, 224, 224, device=DEVICE)
    torch.onnx.export(
        export_model,
        dummy,
        str(destination),
        input_names=["input"],
        output_names=["embedding"],
        dynamic_axes={"input": {0: "batch_size"}, "embedding": {0: "batch_size"}},
        opset_version=17,
    )
    onnx.load(str(destination))


@celery_app.task(name="workers.ewc_worker.retrain_sample")
def retrain_sample(file_path: str, sha256: str, label: str) -> dict[str, Any]:
    """Fine-tune the PyTorch model on a confirmed sample while guarding against forgetting."""

    if label not in CLASS_LABELS:
        raise ValueError(f"Unknown label: {label}")

    fisher_path = settings.model_dir / "fisher_matrix.pkl"
    replay_path = settings.data_dir / "replay_buffer.pkl"
    validation_path = settings.data_dir / "validation_set.pkl"

    fisher_raw = _load_pickle(fisher_path)
    replay_buffer: list[dict[str, Any]] = _load_pickle(replay_path)
    validation_samples: list[dict[str, Any]] = _load_pickle(validation_path)

    fisher = {name: tensor.to(DEVICE) for name, tensor in fisher_raw.items()}
    model = _load_model()
    reference_params = {name: param.detach().clone() for name, param in model.named_parameters()}
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5)

    incoming_image = _preprocess_image(Path(file_path))
    replay_buffer.append(
        {
            "image": incoming_image,
            "label": label,
            "label_index": CLASS_LABELS.index(label),
            "sha256": sha256,
        }
    )
    replay_buffer = replay_buffer[-200:]
    dataset = ReplayDataset(replay_buffer)
    loader = DataLoader(dataset, batch_size=16, shuffle=True)

    model.train()
    last_loss = 0.0
    with mlflow.start_run(run_name=f"ewc_{sha256}", nested=True):
        mlflow.set_tag("trigger", "active_learning")
        mlflow.set_tag("families", json.dumps(sorted({sample["label"] for sample in replay_buffer})))
        for epoch in range(5):
            running_loss = 0.0
            for images, labels in loader:
                images = images.to(DEVICE)
                labels = labels.to(DEVICE)
                optimizer.zero_grad(set_to_none=True)
                logits = model(images)
                task_loss = F.cross_entropy(logits, labels)
                penalty = _ewc_penalty(model, fisher, reference_params)
                loss = task_loss + (EWC_LAMBDA / 2.0) * penalty
                loss.backward()
                optimizer.step()
                running_loss += float(loss.item())

            last_loss = running_loss / max(len(loader), 1)
            _publish(
                {
                    "event": "training_epoch",
                    "epoch": epoch + 1,
                    "total_epochs": 5,
                    "loss": round(last_loss, 6),
                    "sha256": sha256,
                }
            )
            mlflow.log_metric("epoch_loss", last_loss, step=epoch + 1)

        accuracies = _evaluate(model, validation_samples)
        mean_accuracy = float(np.mean(list(accuracies.values()))) if accuracies else 0.0
        mlflow.log_metric("mean_accuracy", mean_accuracy)
        mlflow.log_metric("ewc_loss", last_loss)
        for family, accuracy in accuracies.items():
            mlflow.log_metric(f"acc_{family}", accuracy)

        if mean_accuracy < 0.92:
            _publish(
                {
                    "event": "training_rejected",
                    "sha256": sha256,
                    "mean_accuracy": round(mean_accuracy, 6),
                    "reason": "Validation gate blocked deployment",
                }
            )
            return {"status": "rejected", "mean_accuracy": mean_accuracy}

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            staged_onnx = temp_path / "efficientnet_b1.onnx"
            _export_onnx(model, staged_onnx)
            final_onnx = settings.model_dir / "efficientnet_b1.onnx"
            staged_onnx.replace(final_onnx)

        torch.save(model.state_dict(), settings.model_dir / "efficientnet_b1_pytorch.pth")

        refreshed_fisher = _update_fisher(model, loader)
        with fisher_path.open("wb") as handle:
            pickle.dump({name: tensor.detach().cpu() for name, tensor in refreshed_fisher.items()}, handle)

        with replay_path.open("wb") as handle:
            pickle.dump(replay_buffer, handle)

        version = int(Path(settings.model_dir / "version.txt").read_text(encoding="utf-8").strip() or "0") \
            if (settings.model_dir / "version.txt").exists() else 0
        version += 1
        (settings.model_dir / "version.txt").write_text(str(version), encoding="utf-8")
        mlflow.set_tag("model_version", str(version))

        _publish(
            {
                "event": "training_complete",
                "sha256": sha256,
                "version": version,
                "mean_accuracy": round(mean_accuracy, 6),
            }
        )
        return {"status": "deployed", "version": version, "mean_accuracy": mean_accuracy}
