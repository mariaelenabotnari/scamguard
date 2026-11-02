# Scamguard

**Scamguard** is a web platform that detects coordinated activity and disinformation narrative propagation across public Telegram channels in Moldova.

It collects public channel messages, identifies near-duplicate and semantically equivalent posts published across different channels within short time windows, classifies clusters against known disinformation narratives, and presents transparent, human-verifiable explanations in an interactive dashboard.

---

## Architecture & Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Font Awesome, TanStack Query, React Router, Recharts, Vitest
- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL + `pgvector`, Telethon, APScheduler, pytest
- **ML Pipeline**: `sentence-transformers`, `scikit-learn`, `transformers`, `datasketch` (MinHash/LSH)
- **Infrastructure**: Docker Compose, GitHub Actions CI

---

## Repository Structure

```text
scamguard/
├── docs/                   # Design notes, ADR decisions, API documentation
├── frontend/               # React + TypeScript + Tailwind CSS client
├── backend/                # FastAPI service, collectors, and inference pipeline
├── ml/                     # Offline dataset scripts, notebooks, and model training
├── docker-compose.yml      # Local multi-container stack (db, backend, frontend)
└── .env.example            # Environment variable template
```

---

## Quick Start

### 1. Using Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- **Frontend**: `http://localhost:5173`
- **Backend API**: `http://localhost:8000` (health check at `/health`, OpenAPI docs at `/docs`)

### 2. Local Development

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Backend:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

---

## Ethics & Privacy Principles

- Monitors **only public Telegram channels**.
- Enforces **data minimisation**: raw text of source-deleted posts is purged, retaining only normalised text and hashes.
- Provides **coordination and narrative similarity indicators with full evidence**, keeping human researchers and journalists in the loop rather than claiming automated truth/falsehood judgments.
