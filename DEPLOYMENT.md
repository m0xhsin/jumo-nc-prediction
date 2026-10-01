# Deploy to Vercel

Live application: https://jumo-nc-prediction.vercel.app

Vercel project: `ai-0d53/jumo-nc-prediction` (Hobby).
Database: `jumo-postgres` on Neon's Free plan, Frankfurt, connected to production.
The supplied SQLite records were migrated on 2026-10-01. Do not rerun the initial
migration against this populated database. Future deployments use the existing
database and preserve its data. Preview deployments need a separately configured
database before their API can work.

Deploy the **project root**, not just `frontend/`. The root `vercel.json`
builds React and routes API calls to the Python backend. Production uses
same-origin API requests; leave `VITE_API_BASE` unset.

## Persistent database

Connect a hosted PostgreSQL database (for example Neon through Vercel Storage).
Set `DATABASE_URL` in Vercel's production and preview environment settings.
Use the provider's pooled connection string with SSL enabled. Never put this
secret in a `VITE_` environment variable or commit it.

Before the first deployment, install the serving dependencies and migrate
the existing local SQLite data into an **empty** database:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
read -s DATABASE_URL
export DATABASE_URL
.venv/bin/python backend/migrate_to_postgres.py
unset DATABASE_URL
```

Paste the database connection string when `read` waits for input. The migration
copies sensor configurations, historical orders, and saved predictions. It
refuses to copy into populated target tables. This copies the supplied local
database, not any newer data that may exist only in Azure.

## Deploy

With Node.js 22.12 or newer installed, run from the project root:

```sh
npx vercel login
npx vercel
```

Select your account and create or link the project. Add `DATABASE_URL` in
the Vercel project settings, then deploy production:

```sh
npx vercel --prod
```

Alternatively, import `m0xhsin/jumo-nc-prediction` in Vercel, leaving Root Directory
at the repository root. The local repository remote points to GitHub. The existing
production deployment was created using the CLI; pushing to GitHub alone does not
update it unless the Git integration is connected in Vercel.

Database files are excluded from Git. A fresh clone can use `backend/seed.py` to
initialize sample configurations and historical orders. The migration script is
only for a local copy that contains the original `backend/nc_prediction.db`.

Verify `/health`, the part-number dropdown, a prediction with optional inputs
blank, and saved history after reloading. The full Python training environment
is intentionally excluded; the checked-in trained model performs predictions.

The app's history and deletion endpoints currently have no authentication.
Anyone who can access the deployed app can view or clear its prediction history.
