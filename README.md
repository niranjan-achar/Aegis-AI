# Aegis-AI

Aegis-AI is a multi-modal malware detection platform for Windows PE binaries. It combines binary image analysis, PE header intelligence, byte n-gram statistics, YARA scanning, Grad-CAM explainability, and a continual-learning loop using Elastic Weight Consolidation (EWC).

## What the project includes

- FastAPI backend for file upload, feature extraction, ONNX inference, caching, and explainability.
- React 18 dashboard with scan, evolution, queue, and about pages.
- Celery + Redis worker for low-confidence sample review and continual learning.
- Google Colab notebook for training EfficientNet-B1, exporting ONNX, computing the Fisher matrix, and producing replay-buffer assets.
- Step-by-step text guides for setup, training, deployment, and every backend/frontend module.

## Architecture Overview

1. The frontend uploads a `.exe` or `.dll` to the FastAPI backend.
2. The backend computes the SHA-256 hash and checks Redis for a cached result.
3. On a cache miss, the backend extracts:
   - a binary visualisation image,
   - PE-header and import-table features,
   - byte bigram histogram features.
4. YARA rules run in parallel while the ONNX image encoder and sklearn classification head produce malware family predictions.
5. Grad-CAM maps influential image regions back to file offsets and PE sections.
6. Low-confidence results are added to the active-learning queue and can trigger EWC-based continual fine-tuning through Celery.
7. MLflow tracks model versions, metrics, and deployment decisions.

## Important Notes

- The trained `efficientnet_b1.onnx`, `head.pkl`, `fisher_matrix.pkl`, and `replay_buffer.pkl` files are **not committed**. Generate them with the notebook in [notebooks/train.ipynb](/D:/MCA-RVCE/Projects/Aegis-AI/notebooks/train.ipynb).
- Redis is expected to run through Docker Desktop on Windows.
- Celery on Windows must use `--pool=solo`.

## Quick Start

Read [Guide/start.txt](/D:/MCA-RVCE/Projects/Aegis-AI/Guide/start.txt) first. It walks through environment setup, dependency installation, Redis, backend startup, Celery startup, and frontend startup in exact order.
