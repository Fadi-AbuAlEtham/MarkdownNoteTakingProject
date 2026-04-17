# Markdown Note Taking API

FastAPI backend for personal Markdown notes with:

- users and JWT login
- folders and tags
- notes with revision history
- issue tracking per note/revision
- grammar audit and fix application
- rendered HTML/Markdown with ETag support
- note and folder summarization

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2 async
- PostgreSQL
- Alembic
- JWT via `python-jose`
- LanguageTool for grammar checks
- Gemini for summarization

## Current Project Layout

```text
app/
├── api/            # dependency wiring and auth route
├── core/           # db, config, jwt, security, shared helpers
├── models/         # SQLAlchemy models
├── repositories/   # data access layer
├── routes/         # FastAPI route handlers
├── schemas/        # Pydantic request/response models
└── services/       # business logic
```

## Requirements

- Python 3.11 or newer
- PostgreSQL running locally or remotely
- a virtual environment
- optional:
  - LanguageTool server or public API access
  - Gemini API key for summarization

## Configuration

Create a `.env` file in the repository root.

### Minimum runtime configuration

These values are needed to boot the app and use the core note features:

```env
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/markdown_notes
SECRET_KEY=change_me_to_a_long_random_secret
ALGORITHM=HS256
DB_ECHO=false
```

### Database migration configuration

Alembic uses the synchronous PostgreSQL driver:

```env
DATABASE_URL_SYNC=postgresql+psycopg2://username:password@localhost:5432/markdown_notes
```

### Grammar configuration

Optional. If you do not use grammar endpoints, you can leave these at defaults.

```env
LT_BASE_URL=https://api.languagetool.org
LT_LEVEL=default
# LT_API_KEY=
# LT_AUTH_HEADER=
```

### Summarization configuration

Optional. Required only for summarize endpoints.

```env
GOOGLE_API_KEY=your_gemini_key
# or:
# GEMINI_API_KEY=your_gemini_key

GEMINI_MODEL=gemini-1.5-flash
MAX_CHARS_PER_CALL=12000
LANGUAGE=en
```

### Optional config currently present in `app/core/config.py`

These fields exist in the settings model but are not required by the current runtime path:

```env
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
CACHE_TTL=90
ACCESS_TOKEN_EXPIRE_MINUTES=60
APP_NAME=Markdown Note Taking API
```

## Setup

### 1. Clone and enter the project

```bash
git clone https://github.com/Fadi-AbuAlEtham/MarkdownNoteTakingProject.git
cd MarkdownNoteTakingProject
```

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the database

```bash
createdb markdown_notes
```

Or create it manually in PostgreSQL and point `DATABASE_URL` / `DATABASE_URL_SYNC` to it.

### 5. Run migrations

```bash
alembic upgrade head
```

### 6. Start the API

```bash
uvicorn app.main:app --reload
```

By default:

- app: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## How to Use the App

### Authentication model

- `POST /auth/login` returns a Bearer token
- most content endpoints require `Authorization: Bearer <token>`
- user endpoints are currently public in the codebase

### Typical usage flow

1. Create a user
2. Login
3. Create tags and folders
4. Create a note
5. Update the note to generate revisions
6. Render, summarize, audit grammar, create issues, or restore a revision

## Quick Start API Walkthrough

The examples below use `curl`.

### 1. Create a user

```bash
curl -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "email": "demo@example.com",
    "password": "Passw0rd!",
    "dob": "1998-01-01",
    "phone_number": "123456789"
  }'
```

### 2. Login

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "demo_user",
    "password": "Passw0rd!"
  }'
```

Response:

```json
{
  "access_token": "....",
  "token_type": "bearer"
}
```

Export the token:

```bash
export TOKEN="paste_access_token_here"
```

### 3. Create a tag

```bash
curl -X POST http://127.0.0.1:8000/tags/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "backend"
  }'
```

### 4. Create a folder

```bash
curl -X POST http://127.0.0.1:8000/folders/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Work",
    "parent_id": null
  }'
```

### 5. Create a note

```bash
curl -X POST http://127.0.0.1:8000/notes/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API design",
    "content_md": "# Draft\n\nThs is a markdown note.",
    "folder_id": 1,
    "tag_ids": [1],
    "is_public": false
  }'
```

### 6. Update a note

Each successful update creates a new revision.

```bash
curl -X PUT http://127.0.0.1:8000/notes/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API design updated",
    "content_md": "# Draft\n\nThis note changed.",
    "tag_ids": [1]
  }'
```

### 7. List note revisions

```bash
curl -X GET http://127.0.0.1:8000/revisions/notes/1/revisions \
  -H "Authorization: Bearer $TOKEN"
```

## Main API Endpoints

### Auth

- `POST /auth/login`

### Users

- `GET /users/`
- `GET /users/active/`
- `GET /users/{user_id}`
- `POST /users/`
- `PUT /users/{user_id}`
- `DELETE /users/{user_id}`

### Folders

- `GET /folders/`
- `GET /folders/{folder_id}`
- `GET /folders/{folder_id}/notes/`
- `POST /folders/`
- `PUT /folders/{folder_id}`
- `DELETE /folders/{folder_id}`

### Tags

- `GET /tags/`
- `GET /tags/{tag_id}`
- `POST /tags/`
- `PUT /tags/{tag_id}`
- `DELETE /tags/{tag_id}`

### Notes

- `GET /notes/`
- `GET /notes/{note_id}`
- `POST /notes/`
- `PUT /notes/{note_id}`
- `DELETE /notes/{note_id}`

### Issues

- `GET /issues/`
- `GET /issues/{issue_id}`
- `POST /issues/`
- `PUT /issues/{issue_id}`
- `DELETE /issues/{issue_id}`

### Revisions

- `GET /revisions/`
- `GET /revisions/{revision_id}`
- `GET /revisions/notes/{note_id}/revisions`
- `POST /revisions/`
- `PUT /revisions/{revision_id}`
- `DELETE /revisions/{revision_id}`
- `POST /revisions/notes/{note_id}/revisions/{revision_id}/restore`

### Grammar

- `POST /revisions/notes/{note_id}/revisions/{revision_id}/grammar/audit`
- `POST /revisions/notes/{note_id}/revisions/{revision_id}/grammar/apply-fixes`

### Rendered content

- `GET /revisions/notes/{note_id}/revisions/{revision_id}/render`
- `GET /revisions/notes/{note_id}/revisions/{revision_id}/etag`
- `GET /revisions/notes/{note_id}/revisions/{revision_id}/render-by-etag?etag=...`

### Summarization

- `POST /summarize/notes/{note_id}`
- `POST /summarize/folders/{folder_id}`

## Feature-Specific Usage

### Grammar audit

Run grammar analysis on a specific revision:

```bash
curl -X POST http://127.0.0.1:8000/revisions/notes/1/revisions/2/grammar/audit \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "languagetool",
    "language": "en-US",
    "level": "picky"
  }'
```

Apply suggested fixes and create a new revision:

```bash
curl -X POST http://127.0.0.1:8000/revisions/notes/1/revisions/2/grammar/apply-fixes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "min_severity": "info",
    "strategy": "first_suggestion"
  }'
```

### Rendered content and caching

Render a revision as HTML:

```bash
curl -X GET http://127.0.0.1:8000/revisions/notes/1/revisions/2/render \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: text/html"
```

Render as JSON:

```bash
curl -X GET http://127.0.0.1:8000/revisions/notes/1/revisions/2/render \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

Fetch only the current ETag:

```bash
curl -X GET http://127.0.0.1:8000/revisions/notes/1/revisions/2/etag \
  -H "Authorization: Bearer $TOKEN"
```

If you pass a matching `If-None-Match`, the endpoint returns `304 Not Modified`.

### Summarization

Summarize one note:

```bash
curl -X POST http://127.0.0.1:8000/summarize/notes/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "style": "paragraph",
    "language": "en",
    "max_tokens": 256
  }'
```

Summarize all active notes in a folder:

```bash
curl -X POST http://127.0.0.1:8000/summarize/folders/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "style": "bullets",
    "language": "en",
    "max_tokens": 256
  }'
```

## Development Notes

### Run tests

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### Compile check

```bash
.venv/bin/python -m compileall app tests
```

## Known Notes

- Grammar endpoints depend on the configured LanguageTool endpoint.
- Summarization endpoints require a Gemini API key.
- The integration test suite uses fake grammar/summarize provider overrides so it can verify the app flow without depending on external APIs.
- `passlib` currently emits a non-fatal bcrypt version warning in this environment during password hashing.

## Recommended First Checks After Setup

After starting the app:

1. Open `http://127.0.0.1:8000/docs`
2. Create a user
3. Login and copy the token
4. Click `Authorize` in Swagger
5. Create a folder, tag, and note
6. Update the note once
7. Render or summarize the note

That path exercises the main working flow of the application.
