# GymBuddy Server

FastAPI backend with Supabase authentication and database.

## Setup

1. **Create a virtual environment and install dependencies:**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment variables:**

```bash
cp .env.example .env
```

Fill in your Supabase project credentials in `.env`. You can find these in
your [Supabase dashboard](https://supabase.com/dashboard) under **Settings > API**.

3. **Run the server:**

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
OpenAPI docs are served at `http://localhost:8000/docs`.

## Authentication

The server validates Supabase-issued JWTs. Clients authenticate directly with
Supabase (email/password, social login, etc.) and pass the access token in the
`Authorization: Bearer <token>` header.

Protected endpoints use the `CurrentUserDep` dependency:

```python
from app.dependencies import CurrentUserDep

@router.get("/me")
async def get_me(user: CurrentUserDep):
    return user
```

## Project Structure

```
app/
  main.py          - FastAPI application entry point
  config.py        - Settings loaded from .env
  auth.py          - JWT verification via Supabase JWKS
  dependencies.py  - Reusable FastAPI dependencies
  routers/
    health.py      - GET /health smoke-test endpoint
```
