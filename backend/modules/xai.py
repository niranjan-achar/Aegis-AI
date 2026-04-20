"""Grad-CAM explainability helpers for mapping suspicious pixels back to bytes."""

from __future__ import annotations

import base64
import json
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pefile
import timm
import torch
import torch.nn.functional as F
from PIL import Image
from torchcam.methods import GradCAM

from config import get_settings


DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406], dtype=torch.float32).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225], dtype=torch.float32).view(1, 3, 1, 1)


def _preprocess(image_path: Path) -> torch.Tensor:
    image = Image.open(image_path).convert("RGB").resize((224, 224), Image.Resampling.LANCZOS)
    array = np.asarray(image).astype(np.float32) / 255.0
    tensor = torch.from_numpy(np.transpose(array, (2, 0, 1))).unsqueeze(0)
    tensor = (tensor - IMAGENET_MEAN) / IMAGENET_STD
    return tensor.to(DEVICE)


@lru_cache(maxsize=1)
def get_pytorch_model() -> torch.nn.Module:
    """Load the PyTorch EfficientNet once and keep it resident for Grad-CAM."""

    weights_path = get_settings().model_dir / "efficientnet_b1_pytorch.pth"
    if not weights_path.exists():
        raise FileNotFoundError(
            "Missing backend/models/efficientnet_b1_pytorch.pth. Run notebooks/train.ipynb "
            "and copy the PyTorch checkpoint into backend/models for Grad-CAM support."
        )

    model = timm.create_model("efficientnet_b1", pretrained=False, num_classes=26)
    state_dict = torch.load(weights_path, map_location=DEVICE)
    model.load_state_dict(state_dict)
    model.to(DEVICE)
    model.eval()
    return model


@lru_cache(maxsize=1)
def get_grad_cam() -> GradCAM:
    model = get_pytorch_model()
    return GradCAM(model, target_layer="blocks.6")


def _resolve_section(file_path: Path, offset: int) -> str:
    try:
        pe = pefile.PE(str(file_path))
    except (pefile.PEFormatError, FileNotFoundError, OSError):
        return "unknown"

    for section in pe.sections:
        start = int(section.PointerToRawData)
        end = start + int(section.SizeOfRawData)
        if start <= offset < end:
            return section.Name.decode(errors="ignore").strip("\x00") or "unknown"
    return "unknown"


def generate_gradcam_explanation(
    image_path: Path,
    sha256: str,
    file_path: Path,
    predicted_index: int,
) -> dict[str, Any]:
    """Generate Grad-CAM overlay and map top activations back to file offsets."""

    model = get_pytorch_model()
    cam_extractor = get_grad_cam()
    input_tensor = _preprocess(Path(image_path))

    logits = model(input_tensor)

    activation_map = cam_extractor(class_idx=predicted_index, scores=logits)[0].unsqueeze(0).unsqueeze(0)
    upsampled = F.interpolate(activation_map, size=(224, 224), mode="bilinear", align_corners=False)
    heatmap = upsampled.squeeze().detach().cpu().numpy()
    heatmap = (heatmap - heatmap.min()) / max(heatmap.max() - heatmap.min(), 1e-8)

    image = Image.open(image_path).convert("RGBA").resize((224, 224), Image.Resampling.LANCZOS)
    grayscale = np.asarray(image).astype(np.float32)
    overlay_rgb = np.zeros_like(grayscale)
    overlay_rgb[..., 0] = heatmap * 255
    overlay_rgb[..., 2] = (1 - heatmap) * 180
    blended = np.clip(grayscale * 0.5 + overlay_rgb * 0.5, 0, 255).astype(np.uint8)
    overlay = Image.fromarray(blended, mode="RGBA")

    output_path = get_settings().xai_dir / f"{sha256}_heatmap.png"
    overlay.save(output_path, format="PNG")

    flat_indices = np.argsort(heatmap.flatten())[::-1][:10]
    file_size = max(Path(file_path).stat().st_size, 1)
    top_offsets = []
    for flat_index in flat_indices:
        y, x = divmod(int(flat_index), 224)
        offset = int((y * 224 + x) * (file_size / (224 * 224)))
        top_offsets.append(
            {
                "offset_hex": hex(offset),
                "importance": round(float(heatmap[y, x]), 6),
                "section": _resolve_section(Path(file_path), offset),
            }
        )

    buffer = BytesIO()
    overlay.save(buffer, format="PNG")
    heatmap_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "heatmap_b64": heatmap_b64,
        "heatmap_path": str(output_path),
        "top_offsets": top_offsets,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate Grad-CAM explanation for a binary image.")
    parser.add_argument("image_path", type=Path, help="Path to the 224x224 image")
    parser.add_argument("sha256", type=str, help="File SHA-256")
    parser.add_argument("file_path", type=Path, help="Original binary path")
    parser.add_argument("--class-index", type=int, default=0, help="Predicted class index")
    args = parser.parse_args()

    result = generate_gradcam_explanation(args.image_path, args.sha256, args.file_path, args.class_index)
    print(json.dumps(result, indent=2))
