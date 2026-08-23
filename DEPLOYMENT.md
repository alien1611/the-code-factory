# 🚀 DEPLOYMENT GUIDE: THE CODE FACTORY

This guide covers deploying **The Code Factory** using GitHub Actions, GitHub Pages, Docker / GHCR, and 1-Click Cloud Platforms.

---

## 📑 Table of Contents
1. [Overview & Architecture](#overview--architecture)
2. [Method 1: Frontend to GitHub Pages (Automated CI/CD)](#method-1-frontend-to-github-pages-automated-cicd)
3. [Method 2: Backend to GitHub Container Registry (GHCR)](#method-2-backend-to-github-container-registry-ghcr)
4. [Method 3: 1-Click Cloud Deployment (Render via GitHub)](#method-3-1-click-cloud-deployment-render-via-github)
5. [Method 4: Production Docker Compose](#method-4-production-docker-compose)
6. [Required GitHub Secrets & Environment Variables](#required-github-secrets--environment-variables)

---

## 🏗️ Overview & Architecture

| Component | Technology | Target Deployment | Workflow File |
| :--- | :--- | :--- | :--- |
| **Frontend** | React 18 + Vite + Tailwind CSS | GitHub Pages / Render / Vercel | `.github/workflows/deploy-pages.yml` |
| **Backend** | FastAPI + Python 3.11 + SQLite/Postgres | GHCR Docker / Render / Railway | `.github/workflows/deploy-backend-docker.yml` |
| **CI Validation** | Pytest + Vitest + Build check | GitHub Actions Runner | `.github/workflows/ci.yml` |

---

## 🌐 Method 1: Frontend to GitHub Pages (Automated CI/CD)

The repository includes a GitHub Actions workflow that automatically builds and deploys the frontend web app whenever you push to `combined` or `main`.

### Step 1: Enable GitHub Pages in your Repository
1. Navigate to your GitHub repository: `https://github.com/alien1611/the-code-factory`
2. Go to **Settings** > **Pages** (in the left sidebar).
3. Under **Build and deployment** > **Source**, select **GitHub Actions**.

### Step 2: (Optional) Configure Backend API URL Secret
If your backend is hosted on Render, Railway, or AWS:
1. Go to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret**.
3. Name: `VITE_API_URL`
4. Value: `https://your-backend-service.onrender.com` (your backend URL without trailing slash).

### Step 3: Trigger Deployment
- Push your changes to the `combined` or `main` branch:
  ```bash
  git push origin combined
  ```
- Or go to the **Actions** tab in GitHub > **Deploy Frontend to GitHub Pages** > **Run workflow**.

Your site will be live at:
`https://alien1611.github.io/the-code-factory/`

---

## 🐳 Method 2: Backend to GitHub Container Registry (GHCR)

The backend is automatically packaged as a production Docker image and published to GitHub Container Registry on push to `main`.

### Image URI:
```
ghcr.io/alien1611/the-code-factory-backend:latest
```

### Running the Container:
```bash
docker run -d \
  -p 8000:8000 \
  -e GEMINI_API_KEY="your_gemini_api_key" \
  -e DATABASE_URL="sqlite:///./evidence_verifier.db" \
  --name code-factory-backend \
  ghcr.io/alien1611/the-code-factory-backend:latest
```

---

## ☁️ Method 3: 1-Click Cloud Deployment (Render via GitHub)

A `render.yaml` Blueprint is included for deploying both frontend and backend on [Render.com](https://render.com).

1. Log into **Render** and link your GitHub account.
2. Click **New +** > **Blueprint**.
3. Connect `alien1611/the-code-factory`.
4. Render will automatically read `render.yaml` and provision:
   - `the-code-factory-backend` (FastAPI Web Service)
   - `the-code-factory-frontend` (Static React SPA)
5. Fill in your `GEMINI_API_KEY` in the Render dashboard environment settings.
6. Click **Apply**.

---

## 🖥️ Method 4: Production Docker Compose

To deploy the complete stack on any VPS (AWS EC2, DigitalOcean Droplet, Linode, etc.):

```bash
# 1. Clone the repository
git clone https://github.com/alien1611/the-code-factory.git
cd the-code-factory

# 2. Copy and populate environment variables
cp .env.example .env
# Edit .env and set GEMINI_API_KEY

# 3. Build and launch containers
docker-compose up -d --build

# 4. Verify status
docker-compose ps
```

- Frontend: `http://<your-server-ip>:80`
- Backend API Docs: `http://<your-server-ip>:8000/docs`
- Health Check: `http://<your-server-ip>:8000/api/health`

---

## 🔑 Required GitHub Secrets & Environment Variables

Configure these in **GitHub Settings** > **Secrets and variables** > **Actions**:

| Secret Name | Description | Required |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key for automated invariant reasoning & synthesis | Recommended |
| `VITE_API_URL` | Public URL of the deployed FastAPI backend for frontend API requests | Optional (Defaults to localhost/dynamic) |
| `GITHUB_CLIENT_ID` | GitHub OAuth App Client ID (for OAuth connect flow) | Optional |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth App Client Secret | Optional |
| `GITHUB_WEBHOOK_SECRET` | Webhook verification secret for automated PR event triggers | Optional |

---

## 🧪 Validating Deployment Locally

```bash
# Backend test suite (24 tests)
cd backend && pytest

# Frontend test suite (10 tests)
cd frontend && npm test

# Frontend production build
cd frontend && npm run build
```
