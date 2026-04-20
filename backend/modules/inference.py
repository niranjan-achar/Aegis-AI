"""ONNX-based image inference and sklearn head classification utilities."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import onnxruntime as ort
from PIL import Image

from config import get_settings
from constants import CLASS_LABELS


IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exponentiated = np.exp(shifted)
    return exponentiated / np.sum(exponentiated)


def preprocess_image(image_path: Path) -> np.ndarray:
    """Prepare a PNG image for EfficientNet ONNX inference."""

    image = Image.open(image_path).convert("RGB").resize((224, 224), Image.Resampling.LANCZOS)
    array = np.asarray(image).astype(np.float32) / 255.0
    array = (array - IMAGENET_MEAN) / IMAGENET_STD
    array = np.transpose(array, (2, 0, 1))
    return np.expand_dims(array, axis=0).astype(np.float32)


@lru_cache(maxsize=1)
def get_onnx_session() -> ort.InferenceSession:
    """Load the ONNX encoder produced by the Colab notebook."""

    model_path = get_settings().model_dir / "efficientnet_b1.onnx"
    if not model_path.exists():
        raise FileNotFoundError(
            "Missing backend/models/efficientnet_b1.onnx. Run notebooks/train.ipynb in "
            "Google Colab, download the exported ONNX model, and place it in backend/models."
        )

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    available = ort.get_available_providers()
    selected = [provider for provider in providers if provider in available] or ["CPUExecutionProvider"]
    return ort.InferenceSession(str(model_path), providers=selected)


@lru_cache(maxsize=1)
def get_classification_head() -> Any:
    """Load the sklearn LogisticRegression head trained on combined features."""

    head_path = get_settings().model_dir / "head.pkl"
    if not head_path.exists():
        raise FileNotFoundError(
            "Missing backend/models/head.pkl. Run notebooks/train.ipynb and copy head.pkl "
            "into backend/models before starting inference."
        )
    return joblib.load(head_path)


def run_inference(image_path: Path, feature_vector: list[float]) -> dict[str, Any]:
    """Run the ONNX encoder, concatenate tabular features, and classify the sample."""

    if len(feature_vector) != 306:
        raise ValueError(f"Expected 306 tabular features, received {len(feature_vector)}.")

    session = get_onnx_session()
    head = get_classification_head()
    model_input = preprocess_image(Path(image_path))

    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: model_input})
    embedding = np.asarray(outputs[0]).reshape(-1).astype(np.float32)
    if embedding.size != 1280:
        raise ValueError(
            f"Expected ONNX penultimate embedding to be 1280-dim, received {embedding.size}."
        )

    combined = np.concatenate([embedding, np.array(feature_vector, dtype=np.float32)], axis=0)
    expected_features = getattr(head, "n_features_in_", combined.size)
    head_input = combined if expected_features == combined.size else embedding
    probabilities = None
    if hasattr(head, "predict_proba"):
        probabilities = np.asarray(head.predict_proba(head_input.reshape(1, -1))[0], dtype=np.float32)
    else:
        logits = np.asarray(head.decision_function(head_input.reshape(1, -1))[0], dtype=np.float32)
        probabilities = _softmax(logits)

    top_indices = np.argsort(probabilities)[::-1][:3]
    top3 = [
        {"family": CLASS_LABELS[index], "score": round(float(probabilities[index]), 6)}
        for index in top_indices
    ]
    best_index = int(top_indices[0])

    return {
        "prediction": CLASS_LABELS[best_index],
        "confidence": round(float(probabilities[best_index]), 6),
        "top3": top3,
        "embedding": [round(float(value), 6) for value in embedding.tolist()],
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ONNX malware inference.")
    parser.add_argument("image_path", type=Path, help="Path to the 224x224 PNG")
    parser.add_argument("feature_json", type=Path, help="JSON file containing a 306-dim feature vector")
    args = parser.parse_args()

    features = json.loads(args.feature_json.read_text(encoding="utf-8"))
    result = run_inference(args.image_path, features)
    print(json.dumps(result, indent=2))
