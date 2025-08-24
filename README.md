# StudConnect Backend (FastAPI)

## Quick Start

Create & activate a virtual environment, install dependencies, and run the server:

```bash
python -m venv venv
source venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000/docs for interactive API docs.

## Current Endpoints (v0.2 scaffold)
- `GET /health` health check
- Auth: `POST /auth/register`, `POST /auth/login`
- Users: `GET /users/me`
- Universities: `GET /universities` (filters: `country`, `q`)
- Services: `GET /services` (filter: `category`)
- Bookings: `POST /bookings` (student only), `GET /bookings`
- Scholarships: `GET /scholarships` (filters: `country`, `level`)
- Shortlist: `POST /shortlist` (generate ranked list from preferences)
- Leads: `POST /leads` (in‑memory capture)

## Roadmap (Phase 1 Extended)
- Availability management for counsellors (time slots)
- University/program data ingestion pipeline
- Application tracking entities (applications, documents)
- Email notifications & rate limiting
- Replace in-memory leads & scholarships with DB models
- Role-based admin endpoints

## Phase 2 Ideas
- AI shortlisting recommendations (model integration)
- Admin moderation workflows
- Payment integration
- Content/blog management
- Messaging / chat & real-time presence
- Analytics dashboard

## User Auth / Verification (New)
1. Set env vars (example):
   ```
   DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/dbname?sslmode=require
   JWT_SECRET=change_me_long_random
   OTP_SENDER=debug
   ```
2. Endpoints:
   - POST /auth/register  -> sends OTP
   - POST /auth/verify    -> verify code, returns JWT
   - POST /auth/login     -> login (after verification)
   - GET  /users/me       -> requires Bearer token
3. OTP is 6 digits, expires in 5 minutes.

## Email / OTP (SMTP)
Set these environment variables to enable real OTP emails:
```
SMTP_HOST=smtp.yourprovider.com
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password_or_app_password
SMTP_FROM=notifications@yourdomain.com   # optional (defaults to SMTP_USER)
OTP_EXP_MIN=5                             # optional OTP validity (minutes)
```
If SMTP variables are missing, the server falls back to logging the OTP (development mode).

## How is data upserted into the database?

The upsert logic is handled in `db/universities_upload.py` using a SQL `INSERT ... ON CONFLICT ... DO UPDATE` statement:

- For each row in the CSV, the script tries to insert a new row into the `universities` table.
- If a row with the same `(name, country)` already exists (as defined by the `UNIQUE(name, country)` constraint), the statement updates all columns with the new data instead of inserting a duplicate.
- This ensures that:
  - New universities are inserted.
  - Existing universities are updated with the latest data from the CSV.

**Code reference:**
```python
cur.execute("""
    INSERT INTO universities (...columns...)
    VALUES (...values...)
    ON CONFLICT (name, country)
    DO UPDATE SET
        ...all columns updated...
""", {...})
```

**How to verify upsert:**
- After running the script, connect to your database and run:
  ```sql
  SELECT * FROM universities;
  ```
- You should see all rows from your CSV, with the latest data for each university.
- If you run the script again with changed data, the affected rows will be updated, not duplicated.

**Note:**  
If you want to log or debug upserts, you can add a print statement after each `cur.execute` to confirm which rows were inserted/updated.
