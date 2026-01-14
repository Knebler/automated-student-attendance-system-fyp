## Purpose

This file gives immediate, actionable orientation for AI coding agents working on this repository. Focus: architecture, developer workflows, important gotchas and exact entry points to change behavior safely.

---

### Big picture (what to know first)

- This is a Flask-based web app split using a BCE structure:  *Boundaries* (Flask Blueprints) -> *Controls* (business logic) -> *Entities* (data models). See `application/__init__.py` and the three folders `application/boundaries`, `application/controls`, `application/entities` for concrete examples.
- App entry point: `app.py` (factory `create_flask_app`) — it registers blueprints, sets up SQLAlchemy (`app.config['db']`) and initializes Firebase (Pyrebase). Use this file to understand app startup and extension wiring.

### Data layer & important gotchas

- The code historically mixed two DB patterns, but the repo has been refactored to prefer SQLAlchemy:
   - SQLAlchemy session stored at `app.config['db']` (set in `app.py`) is now the primary data-access path.
   - `application/entities/base_entity.py` provides compatibility wrappers (`execute_query`, `get_db_connection`) so existing modules still work but will use SQLAlchemy when `app.config['mysql']` is not present.
    - Standalone helper scripts under `helper/db/*` (mysql.connector) still use direct MySQL connections for schema setup/dummy data — these are out-of-band tools and can remain using mysql-connector.
    - We added a SQLAlchemy migration helper at `helper/db/migrate_sqlalchemy.py` — this runs `database/schema.sql` using SQLAlchemy's engine (mysql+pymysql) so you can create the full schema through the ORM tooling without direct mysql client calls.
- Many entity classes use `TABLE_NAME` and implement `create_table(app)` with raw SQL strings — see `application/entities/*.py` for examples. This repository favors explicit CREATE TABLE SQL for schema management.

### Firebase & AI integrations

- Firebase authentication is used via Pyrebase (`app.config['firebase_auth']`) and an admin service account sits in `instance/firebase_service_account.json` when needed.
- The `src/ai_model.py` file is present but currently empty. Any AI-related work (model calls, pipelines) should be added under `src/` and must be wired into `application/` controls if it will affect routes.

### How the app is started locally

1. Create a Python venv and install dependencies (Windows PowerShell):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Set environment variables or an `.env` file (README references `.env.example` but it may be missing) — the app reads configuration from `config.py` (dotenv). Required: MYSQL_*, FIREBASE_* keys.

3. Initialize database (pick one):
   - Run SQL schema: `mysql -u root -p < database/schema.sql` OR
   - Use helper script `helper/db/create_database.py` which creates the DB and populates dummy data.

4. Start app (development):

   ```powershell
   python app.py
   # Then open http://localhost:5000
   ```

Note: `app.py` will run `create_db()` and write `.db_initialized` on first run. The app now prefers SQLAlchemy and `app.config['db']` — `app.config['mysql']` is no longer required for application code (helper scripts still use it).

### Common patterns agents should follow

- Adding HTTP routes: create a new blueprint under `application/boundaries/`, implement business logic in `application/controls/`, and add/extend entity functions in `application/entities/`. Register the blueprint in `application/__init__.py`.
- Database schema changes: modify `database/schema.sql` and/or the entity `create_table()` methods. For local testing, run `helper/db/create_database.py` so schema + dummy data is created.
 - Data access: prefer SQLAlchemy and the helpers in `application/entities/base_entity.py` (`execute_query`, `get_db_connection`). These will route to SQLAlchemy if `app.config['mysql']` is not configured, so aim to use them rather than raw connectors.

### Files to inspect for further context (quick links)
- Startup & config: `app.py`, `config.py` (root), `instance/firebase_service_account.json` (secrets)
- Architecture: `application/__init__.py`, `application/boundaries/*`, `application/controls/*`, `application/entities/*`
- DB helpers & schema: `helper/db/*`, `database/schema.sql`, `dummy_data/*.py`
- AI model placeholders: `src/ai_model.py` (currently empty)

### When you see failing DB calls

- If code expects `app.config['mysql']` but it is not set, either:
  - Wire a Flask MySQL connector (e.g., `flask_mysqldb`) into the app factory in `app.py`, or
  - Refactor that module to use the SQLAlchemy session available at `app.config['db']`.

### Short maintenance checklist for new AI agent work

1. Prefer small, reversible changes; ensure you run the app locally with MySQL available.
2. If adding AI model code: place new modules under `src/` and call them from `application/controls/` rather than embedding heavy CPU work in handlers.
3. Keep secrets out of the repo — use `instance/` for service accounts and `.env` for runtime keys.

---

If anything in this file looks wrong or incomplete (I may have missed a repo-specific run script), tell me which area you want expanded and I’ll update this guidance. Thank you! ✅
