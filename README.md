# 🏭 THE CODE FACTORY
> Evidence-Driven Automated Verification Engine for Code Changes & Pull Requests

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react)](https://reactjs.org)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF.svg?logo=vite)](https://vitejs.dev)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB.svg?logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-100%25%20Passing-brightgreen.svg)]()
[![GitHub Actions CI](https://img.shields.io/badge/GitHub_Actions-CI_Passing-2088FF.svg?logo=github-actions)](https://github.com/alien1611/the-code-factory/actions)
[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-Deployed-22c55e.svg?logo=github)](https://alien1611.github.io/the-code-factory/)

---

## 🚀 Quick Deployment

Full deployment instructions are available in [DEPLOYMENT.md](DEPLOYMENT.md).

- **GitHub Pages (Frontend):** Automated via [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml).
- **Docker / GHCR (Backend):** Automated via [`.github/workflows/deploy-backend-docker.yml`](.github/workflows/deploy-backend-docker.yml).
- **1-Click Render Cloud:** Uses [`render.yaml`](render.yaml).
- **Local / VPS Docker Stack:** Run `docker-compose up -d --build`.

## 🏗️ Architecture & Monorepo Directory Layout

```
the-code-factory/
├── backend/          # FastAPI REST API, Quota Engine, Orchestrator, & DB Models
│   ├── app/
│   │   ├── api/          # Endpoints: /auth, /repositories, /pull-requests, /verifications, /quota
│   │   ├── core/         # Config, Security & Logging
│   │   ├── database/     # SQLAlchemy Base & Models (UserQuota, Verification, Finding, etc.)
│   │   ├── integrations/ # AICodeVerifierModule & Adapter interface
│   │   └── services/     # VerificationOrchestrator, DockerService, LLMService, QuotaService
│   ├── tests/            # Full Pytest test suite (24 tests)
│   └── requirements.txt  # Backend dependencies
├── frontend/         # React 18 + Vite + Tailwind CSS User Interface
│   ├── src/
│   │   ├── components/   # Navbar, 3D FactorySequence, VerdictStamp, SummaryGrid, IssueCard
│   │   ├── screens/      # LandingScreen, ConnectScreen, RepoSelectionScreen, ProgressScreen, ResultsScreen
│   │   └── lib/          # API client, types, and mock data
│   ├── tests/            # Vitest unit test suite (10 tests) + Playwright E2E suite (2 tests)
│   └── package.json
└── verifier/         # Core AI & AST Verification Engine (from combined branch)
    ├── parser.py         # Tree-sitter CST / AST syntax parser (Python, JS, C++, Java)
    ├── code_parser.py    # Python profile and signature parser
    ├── verifier.py       # Gemini AI requirement invariant synthesis
    ├── test_generator.py # Automated property test generator
    ├── aggregator.py     # Pytest JSON execution reporter & proof aggregator
    └── tests/generated/  # Synthesized invariant proof test cases
```

---

## ⚡ Quickstart Guide

### 1. Run the Backend API Server
```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
* **Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Health Check:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

### 2. Run the Frontend Dashboard
```bash
cd frontend
npm install
npm run dev
```
* **Web UI:** [http://localhost:5173](http://localhost:5173)

---

## 🧪 Quality Assurance & Test Verification

```bash
# Backend Pytest Suite (24/24 Passed)
cd backend && pytest -v

# Frontend Vitest Suite (10/10 Passed)
cd frontend && npm test

# Playwright End-to-End Suite (2/2 Passed)
cd frontend && npm run test:e2e
```
