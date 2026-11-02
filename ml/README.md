# Scamguard ML Workspace

This directory holds offline data collection, exploratory notebooks, label mapping, model training, and evaluation scripts.

## Structure

- `data/raw/`: Downloaded raw datasets (git-ignored).
- `data/processed/`: Cleaned and split datasets (git-ignored).
- `notebooks/`: EDA and error analysis notebooks.
- `scripts/`: Reproducible CLI scripts (`download`, `clean`, `label_map.yaml`, `train`, `evaluate`).

> **Rule**: The backend (`backend/app/ml/`) only loads trained artifacts for inference. Training code never runs inside the FastAPI server.

