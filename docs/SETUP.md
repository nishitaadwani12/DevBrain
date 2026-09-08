# Setup

## Prerequisites
- Python 3.12+
- Node 18+
- Free accounts: [Google AI Studio](https://aistudio.google.com/apikey) (Gemini key), [Supabase](https://supabase.com) (project)

## 1. Supabase
1. Create a project and wait for it to provision.
2. Open **SQL Editor** and run the contents of [`docs/schema.sql`](schema.sql).
3. Copy these into your backend `.env`:
   - `Project Settings > API` → `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`
   - `Project Settings > API > JWT Settings` → `SUPABASE_JWT_SECRET`
   - `Project Settings > Database` → connection string → `DATABASE_URL`

## 2. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values
uvicorn app.main:app --reload
```
API runs at http://localhost:8000 (interactive docs at `/docs`).

Run tests any time with:
```bash
cd backend && ./.venv/bin/python -m pytest
```

### Local single-user mode (no auth)
For quick local iteration without Supabase auth, set `AUTH_ENABLED=false` in
`backend/.env`. All data is attributed to `DEV_USER_ID`. You still need
`GEMINI_API_KEY` and `DATABASE_URL`.

## 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env   # fill in real values
npm run dev
```
App runs at http://localhost:5173.

- With `VITE_SUPABASE_URL` set → real email/password login.
- With `VITE_SUPABASE_URL` empty → dev mode, no login (pair with backend `AUTH_ENABLED=false`).

## Deployment (all free tiers)

### Backend → Render
1. Push this repo to GitHub.
2. In Render, create a **Blueprint** and point it at the repo — it reads [`render.yaml`](../render.yaml).
3. Fill the secret env vars (Gemini, Supabase, `DATABASE_URL`, `CORS_ORIGINS` = your Vercel URL).
4. Deploy. Note the service URL (e.g. `https://devbrain-api.onrender.com`).

### Frontend → Vercel
1. Import the repo in Vercel, set **Root Directory** to `frontend/`.
2. Add env vars: `VITE_API_URL` (Render URL), `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
3. Deploy. [`frontend/vercel.json`](../frontend/vercel.json) handles SPA routing.

### Database/Auth/Storage → Supabase (already hosted)

> Note: Render's free tier spins the service down when idle; the first request
> after a cold start takes a few seconds.
