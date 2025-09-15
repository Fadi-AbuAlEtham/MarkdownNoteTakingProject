# Note Markdown API

A FastAPI backend for Markdown notes with folders, tags, revisions (versioning), grammar audits, AI summarization, and smart HTTP caching for rendered content.

---

## Features

### Notes & Folders
- Create, update, soft-delete notes  
- Tags (many-to-many)  
- Per-user data isolation  

### Revisions (versioning)
- Every note update automatically creates a snapshot (`note_revisions`)  
- Restore from any revision  

### Grammar audit
- Pluggable provider (LanguageTool currently)  
- Run audits and optionally apply fixes (creates a new revision / updates note)  

### Summarization (Gemini)
- Summarize note content with Google Gemini (free tier available)  

### Rendered HTML with HTTP caching
- ETag + Last-Modified support  
- `304 Not Modified` when client is fresh  

### Auth
- JWT Bearer (HS256)  

---

## Stack
- Python (FastAPI, Pydantic v2, SQLAlchemy 2 (async), asyncpg)  
- PostgreSQL  
- JWT via python-jose  
- LanguageTool for grammar audits  
- Google Gemini for summarization  

---

## Project Structure (MVC-ish)
```
app/
├─ api/ # API assembly (router)
├─ controllers/ # FastAPI route handlers (HTTP layer)
├─ core/ # config, db, utils, auth helpers
├─ models/ # SQLAlchemy ORM models
├─ repositories/ # DB access (queries, persistence)
├─ schemas/ # Pydantic models (request/response)
├─ services/ # Business logic layer
│ └─ providers/ # External provider adapters (LanguageTool, Gemini)
└─ main.py # FastAPI app entrypoint
```
---

## Requirements
- Python 3.11+ (3.12/3.13 fine)  
- PostgreSQL 14+ running locally (or a cloud instance)  
- A Gemini API Key (free): https://aistudio.google.com/app/apikey  


---

##  Configuration

All settings are loaded from `.env` (using Pydantic `BaseSettings`).  
Do not commit your real `.env`. Ship a `.env.example` for others.

### `.env.example`

```env
# --- App / DB ---
APP_NAME=Note Markdown API
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/markdown_notes
DATABASE_URL_SYNC=postgresql+psycopg2://username:password@localhost:5432/markdown_notes
DB_ECHO=false

# --- JWT ---
SECRET_KEY=change_me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# --- LanguageTool (Grammar) ---
LT_BASE_URL=https://api.languagetool.org
LT_LEVEL=default
# LT_API_KEY=
# LT_AUTH_HEADER=

# --- Gemini (Summarize) ---
# Provide either one:
GOOGLE_API_KEY=your_gemini_key
# GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-1.5-flash
MAX_CHARS_PER_CALL=12000
LANGUAGE=en

# --- Redis (optional) ---
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL=90
```
---

## Getting Started

```bash
# 1) Clone & enter
git clone https://github.com/Fadi-AbuAlEtham/MarkdownNoteTakingProject.git
cd MarkdownNoteTakingProject

# 2) Create env from example
cp .env.example .env
# edit values as needed (DB URL, JWT SECRET, Gemini key, etc.)

# 3) Create and activate venv
python -m venv .venv
source .venv/bin/activate      # on Windows: .venv\Scripts\activate

# 4) Install deps
pip install -r requirements.txt   

# 5) Ensure PostgreSQL database exists
# createdb markdown_notes  (or create via GUI / psql)

# 6) Run the app
uvicorn app.main:app --reload
# App on http://localhost:8000
```