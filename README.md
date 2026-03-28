# Pen Storage Company (PSC) Web App

PSC is a Flask + SQLAlchemy web app for managing a pen lending/donation program. It includes member workflows (loan, donate, return), admin/sector dashboards, and a real-time customer support chat. A Gemini-powered assistant responds to member questions through `/chat`.

## Features
- Member auth (register/login/logout)
- Pen inventory with PRS (Pen Rating Score)
- Loan, donation, and return workflows
- Sector dashboards for operations, archive, security, etc.
- Real-time SoBAB support chat via Socket.IO
- Gemini-powered assistant endpoint (`/chat`)

## Tech Stack
- Flask
- Flask-Login
- Flask-SQLAlchemy
- Flask-SocketIO + eventlet
- PostgreSQL (via SQLAlchemy)
- TextBlob sentiment scoring
- Google GenAI (Gemini)

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional but recommended
export SECRET_KEY="change-me"
export GEMINI_API_KEY="your-gemini-key"

python app.py
```
Then open `http://localhost:5000`.

## Environment Variables
These are all optional; sensible (but not production-safe) defaults exist in `app.py`.

- `DATABASE_URL`: SQLAlchemy DB URL (defaults to the built-in Postgres URL in code)
- `SECRET_KEY`: Flask session secret
- `GEMINI_API_KEY`: required for `/chat` responses
- `GEMINI_MODEL`: defaults to `gemini-3.1-flash-lite-preview`
- `ADMIN_PASSWORD_HASH`: PBKDF2 hash for admin elevation
- `SECTOR_PASSWORD_HASH_SODAC`
- `SECTOR_PASSWORD_HASH_SOBAB`
- `SECTOR_PASSWORD_HASH_SORASR`
- `SECTOR_PASSWORD_HASH_SOCAC`
- `SECTOR_PASSWORD_HASH_SOSAS`
- `SECTOR_PASSWORD_HASH_SOARC`

To generate PBKDF2 hashes with Werkzeug:
```bash
python - <<'PY'
from werkzeug.security import generate_password_hash
print(generate_password_hash("your-password", method="pbkdf2:sha256"))
PY
```

## App Routes (Highlights)
- Public: `/`, `/about`, `/partnerships`
- Auth: `/register`, `/login`, `/logout`
- Member: `/dashboard`, `/loan`, `/donate`, `/return_loan/<loan_id>`
- Support: `/support` (customer chat)
- Admin/Sectors: `/sectors`, `/sector/<sector>`

Sectors available: `sodac`, `sobab`, `sorasr`, `socac`, `sosas`, `soarc`.

## Running in Production
Flask-SocketIO works best with eventlet. A simple production launch:
```bash
gunicorn -k eventlet -w 1 app:app
```

## Data Initialization
The app creates tables on startup (`db.create_all()` in `app.py`). No separate migration step is required for a fresh database.

## File Structure
- `app.py`: main application
- `templates/`: HTML views
- `static/`: CSS, JS, and uploaded pen photos (`static/pens/`)
- `migrations/`: existing migration artifacts (if used)

## Notes
- Uploads are stored under `static/pens/`.
- If `GEMINI_API_KEY` is not set, `/chat` returns a configuration message.

## License
TBD
