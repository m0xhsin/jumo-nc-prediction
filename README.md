# JUMO Laser Trimming Optimizer

A university team project that uses machine learning to recommend nominal correction values before laser trimming platinum thin-film resistance sensors.

**[Live demo](https://jumo-nc-prediction.vercel.app)**

## Features

- Select a sensor part number and load its default configuration.
- Enter sputtering and substrate measurements to generate an XGBoost prediction.
- Use historical averages when optional screen-printing parameters are omitted.
- Explore tolerance, feature-impact, and yield visualizations.
- Save prediction inputs, results, timestamps, and model versions in PostgreSQL.

## Technology

| Component | Technology |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS |
| API | Python, FastAPI, SQLAlchemy |
| Model | XGBoost regression |
| Database | Neon PostgreSQL |
| Hosting | Vercel |

## Run locally

Use Python 3.12 and Node.js 22.12 or later. On macOS, XGBoost also requires OpenMP (`brew install libomp`).

```sh
git clone https://github.com/m0xhsin/jumo-nc-prediction.git
cd jumo-nc-prediction
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt uvicorn
cd backend
python seed.py
uvicorn app.main:app --reload
```

In another terminal, from the repository root:

```sh
cd frontend
npm ci
npm run dev
```

The frontend uses `http://127.0.0.1:8000` during development. The API documentation is available at `http://127.0.0.1:8000/docs`. Local development defaults to SQLite; setting `DATABASE_URL` selects a hosted database.

## Project structure

```text
api/                 Vercel entrypoint
backend/app/         API routes, schemas, database models, and trained model
frontend/            React application
notes/               Original project and modeling notes
requirements.txt     Minimal prediction-serving dependencies
vercel.json          Frontend build and API routing
DEPLOYMENT.md        Hosting and database setup
```

The trained prediction model is included. Raw manufacturing datasets, database files, notebook outputs, internal reference documents, and credentials are excluded. Retraining requires the original datasets and the separate dependencies in `backend/requirements.txt`.

## Deployment

The current deployment runs on Vercel with persistent Neon PostgreSQL storage. See [DEPLOYMENT.md](DEPLOYMENT.md) for configuration and deployment commands. The original project notes describe the former Azure deployment and remain as historical documentation.

This is a demonstration application. Predictions require human review. The demo has no user authentication, so visitors can view and clear the shared prediction history. Do not enter confidential information into the public demo.
