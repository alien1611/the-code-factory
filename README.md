# Evidence-Driven Verification Engine for AI Code Changes

Backend & GitHub Infrastructure service built with **Python 3.11**, **FastAPI**, **SQLAlchemy**, **Docker Sandbox**, and **Gemini LLM**.

The system receives a GitHub Pull Request and determines whether the code change can be trusted using independently generated evidence from isolated test runs, security scans, static analysis, and regression checks.

---

## 🚀 Key Features

- **GitHub Integration:** Full PR metadata, commit tree, unified diff extraction, and changed file analysis.
- **Async Verification Jobs:** Immediate `202 Accepted` response with non-blocking lifecycle orchestration (`QUEUED` → `CLONING` → `PREPARING` → `ANALYZING` → `VERIFYING` → `AGGREGATING` → `COMPLETED`).
- **Sandboxed Execution:** Safe, isolated Docker container execution with `--network none`, memory limits, CPU caps, and strict timeouts.
- **Deterministic Verdict Engine:** Rules-based evaluation of evidence (`VERIFIED`, `VERIFIED_WITH_RISKS`, `REJECTED`, `INCONCLUSIVE`).
- **Evidence-Grounded AI Explanation:** Uses Gemini to explain the findings and test results clearly to developers without fabricating claims.
- **Modular Integration Contract:** Standardized contract for teammate analysis plugins.

---

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and configure your keys:
```bash
cp backend/.env.example backend/.env
```
Key variables:
- `GITHUB_TOKEN`: Personal Access Token for GitHub API access.
- `DATABASE_URL`: `sqlite:///./evidence_verifier.db` or `postgresql://postgres:postgres@localhost:5432/evidence_verifier`.
- `GEMINI_API_KEY`: API key for Gemini model explanation layer.
- `DOCKER_ENABLED`: Set to `true` to enable Docker sandbox execution.

### 3. Run Backend Server
```bash
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload
```

Server will be running at `http://localhost:8000`.
- API Docs (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 4. Run Test Suite
```bash
python -m pytest backend/tests/ -v
```

---

## 📦 Docker Compose Deployment

To run the backend with PostgreSQL in Docker:
```bash
cd backend
docker-compose up --build
```
