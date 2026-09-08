# Setup

## Prerequisites
- Python 3.12+
- Node 18+
- Free accounts: [Google AI Studio](https://aistudio.google.com/apikey) (Gemini key), [Supabase](https://supabase.com) (project)

## 1. Supabase
1. Create a project. Wait for it to provision.
2. In **SQL Editor**, enable pgvector and create tables (schema added in Phase 1):
   ```sql
   create extension if not exists vector;
   ```
3. Copy `Project Settings > API` values into your `.env` files.

## 2. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real values
uvicorn app.main:app --reload
```
API runs at http://localhost:8000 (docs at `/docs`).

## 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env   # fill in real values
npm run dev
```
App runs at http://localhost:5173.

## Deployment (free)
- **Frontend** → Vercel (import repo, root `frontend/`)
- **Backend** → Render (web service, root `backend/`, start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`)
- **DB/Auth/Storage** → Supabase (already hosted)
