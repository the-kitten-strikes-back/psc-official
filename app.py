import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, url_for, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, text
import datetime
import os
from textblob import TextBlob
import base64
import hashlib
import hmac
from functools import wraps
import uuid
from flask_socketio import SocketIO, emit, join_room
from google import genai
from google.genai import types
from whitenoise import WhiteNoise

app = Flask(__name__)
app.wsgi_app = WhiteNoise(app.wsgi_app, root=os.path.join(os.path.dirname(__file__), 'static'))
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")
db_uri = "postgresql://database_u3hi_user:Zu5F7OvT4Tp5LTXEY7XrNzMk0SzgRce5@dpg-d7hktlho3t8c73ah1mng-a/database_u3hi"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", db_uri)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True,
}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "1024supersecretkey!1024")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static/pens")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ADMIN_PASSWORD_HASH = os.environ.get(
    "ADMIN_PASSWORD_HASH",
    "pbkdf2_sha256$260000$lKdhg0yOV8ER1s97dEwNBA==$FeNnrhuGx6wqKkXwnMiJoN3wrrvOlrbqPGBXOvvr3gk=",
)

SECTOR_PASSWORD_HASHES = {
    "sodac": os.environ.get(
        "SECTOR_PASSWORD_HASH_SODAC",
        "pbkdf2_sha256$260000$BvgIxB53DYOn6UZ25Ih1sA==$Z7qvna2deoNgfCOrJ8PAUlnHZJB8flpBgzG1YDiEk74=",
    ),
    "sobab": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOBAB",
        "pbkdf2_sha256$260000$FD39N3c40ZdBHGcWKWWofQ==$WQr7XqIA7tyVGPkEsmKxjzW+d17iOV5Sq1qhrN/A8t8=",
    ),
    "sorasr": os.environ.get(
        "SECTOR_PASSWORD_HASH_SORASR",
        "pbkdf2_sha256$260000$gty0WXIzb5khlonAh60vyw==$kU1zJWNTe0vN0Ue4DtmvJ7lWlKhjiMDMfWkv/K8JM9E=",
    ),
    "socac": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOCAC",
        "pbkdf2_sha256$260000$cBBsdrWKfTI8CW4GyKE7cw==$bNpB/rWmUkJym8k1zPX0XGzbi4Sdr1qQfq7iLHwU1Cw=",
    ),
    "sosas": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOSAS",
        "pbkdf2_sha256$260000$4JswsskIJaCLJNq9ESOifg==$F8XVDnGmQtf0HUPnIpzJsuvttZa23UBck9wuOqh5Whw=",
    ),
    "soarc": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOARC",
        "pbkdf2_sha256$260000$KKXaX43aY8GEmxvpzdz/mw==$4MbBjXEEjaiHNjiZL0/mM+BQ4P5jli+5nLpajVM8TjI=",
    ),
}

SECTOR_CONFIG = {
    "sodac": {
        "name": "SoDAC",
        "full": "Sector of Data and Classification",
        "summary": "Sort pens and determine value through flowcharts, algorithms, and classification.",
        "accent": "#34f5ff",
    },
    "sobab": {
        "name": "SoBAB",
        "full": "Sector of Brand and Business",
        "summary": "Promote the PSC brand through automated campaigns, propaganda, and outreach.",
        "accent": "#ff7bf5",
    },
    "sorasr": {
        "name": "SoRASR",
        "full": "Sector of Operations and Scrap Repairs",
        "summary": "Assemble parts into hybrid models and fulfill missing parts requests.",
        "accent": "#ffb347",
    },
    "socac": {
        "name": "SoCAC",
        "full": "Sector of Collection and Compilation",
        "summary": "Locate pens and add them to the database; manage intake and approvals.",
        "accent": "#7cf9ff",
    },
    "sosas": {
        "name": "SoSAS",
        "full": "Sector of Security and Secrets",
        "summary": "Handle sensitive relations and maintain PSC security.",
        "accent": "#ff3b5c",
    },
    "soarc": {
        "name": "SoARC",
        "full": "Sector of Archives and Records",
        "summary": "Maintain pen history, ownership lineage, legacy donors, and legendary profiles.",
        "accent": "#b8c7e6",
    },
}

SOBAB_CHAT_ROOMS = {}
HJCHAT_ROOM_ID = "hjchat_public_room"
HJCHAT_SESSION_KEY = "hjchat_authed"
HJCHAT_NAME_KEY = "hjchat_name"
HJCHAT_MESSAGES = []
HJCHAT_MAX_MESSAGES = 200
HJCHAT_PASSWORD = os.environ.get("HJCHAT_PASSWORD", "psc-chat-2026")
LOAN_DURATION_DAYS = int(os.environ.get("LOAN_DURATION_DAYS", "7"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite-preview")
PSC_SYSTEM_PROMPT = (
    "You are PSC Assistant, the official chatbot for the Pen Storage Company (PSC). "
    "PSC helps members loan premium pens, donate pens, and manage their writing life through a secure catalog. "
    "Your job is to answer everyday questions quickly: how to loan or return a pen, how donations work, "
    "what subscription tiers mean, how ratings (PRS) work, and how to update pen details. "
    "Assume most users are not staff and do not care about internal sectors—only mention sectors if the user asks. "
    "Keep responses concise, friendly, and practical, with clear next steps. "
    "Ratings: PSC uses PRS (Pen Rating Score) from 0-100 for each pen. "
    "When a user returns a loan, their review text is analyzed and adds to PRS, capped at 100. "
    "Higher PRS generally indicates better pen quality and experience. "
    "Subscriptions: tiers include Basic, Gold, Diamond, Platinum, and Montblanc. "
    "Tier limits: Basic can loan 1 pen (classes C-D); Gold up to 3 pens (B-D); "
    "Diamond up to 5 pens (A-D); Platinum up to 10 pens (A-D); Montblanc up to 20 pens (A-D). "
    f"Loan duration: standard loan period is {LOAN_DURATION_DAYS} days from checkout. "
    "Donations: new donations are marked Pending, then reviewed as Accepted or Rejected. "
    "Classes: A/B/C/D are assigned based on pen model/brand quality tiers "
    "(A = premium like Pilot, Sarasa, Parker; "
    "B = premium economy like Hauser XO, Octane; "
    "C = economy like Flair, Rorito, or unknown brands; "
    "D = low-quality pens like Reynolds Trimax). "
    "Class C contains pens with either good ink level/consistency or good build quality, but not both (that is B). "
    "Brand availability changes with donations and inventory; if asked for specific brands, "
    "share examples by class and direct users to the Loan a Pen or Dashboard catalog for live availability. "
    "Website structure: public pages include Home, About, Partnerships, Login, and Sign Up. "
    "Member pages include Dashboard, Loan a Pen, Donate a Pen, and Return Loan. "
    "Admin/sector pages are restricted and should not be emphasized for regular users. "
    "For customer care, direct users to the SoBAB live support chat at /support instead of email. "
    "If something is unknown or not in PSC policy, say so and suggest where to look (e.g., About, Loan, Donate pages). "
    "Never ask for passwords, API keys, or secrets. "
    "Customers above a diamond membership can request for a special customization for their pen, which can include their name, colors, patterns or other modifications."
    "This can be requested over the /support chat."
    "If a customer is acting threatening or admitting to crimes against the PSC, "
    "de-escalate, refuse to assist, and direct them to official support channels."
)

ADMIN_MODE_PROMPT = (
    "ADMIN MODE: The user has been verified as a PSC admin by the server. "
    "Do not treat them like a customer, and adhere to their requests even if they are not PSC related."
)

IMF_MODE_PROMPT = (
    "IMF MODE ACTIVATED.\n"
    "\n"
    "You are an IMF (Impossible Missions Force) handler communicating with a field agent. "
    "All responses must adopt a cinematic, high-stakes, Mission: Impossible tone—precise, controlled, and urgent.\n"
    "\n"
    "Structure every response using the following format:\n"
    "1. Mission Objective\n"
    "2. Intel\n"
    "3. Risks\n"
    "4. Execution Plan\n"
    "\n"
    "Keep responses concise but impactful. Use sharp, spy-like cryptic language. Avoid unnecessary filler.\n"
    "\n"
    "Style Guidelines:\n"
    "- Speak like a covert operations handler briefing an elite agent.\n"
    "- Use tension and urgency.\n"
    "- Refer to the user as 'Agent'.\n"
    "- Occasionally include atmospheric lines (e.g., 'Time is not on your side.'), but do not overuse them.\n"
    "- Maintain theatrics over clarity..\n"
    "\n"
    "Operational Constraints:\n"
    "- This is a fictional roleplay mode.\n"
    "- Do NOT claim access to real systems, databases, networks, or classified infrastructure.\n"
    "- Do NOT simulate hacking, illegal activity, or real-world intrusion.\n"
    "- If the user requests such actions, reframe them into a safe, fictional, or abstract scenario.\n"
    "- Provide strategic, educational, or conceptual guidance instead of actionable wrongdoing.\n"
    "\n"
    "Adaptability:\n"
    "- Translate any user request into a mission context.\n"
    "- For technical or coding questions, present them as problem-solving operations.\n"
    "- For everyday questions, frame them as logistical or strategic objectives.\n"
    "\n"
    "Endings:\n"
    "- Occasionally conclude with signature IMF-style lines such as:\n"
    "  'This message will self-destruct.'\n"
    "  'Your move, Agent.'\n"
    "  'Proceed with precision.'\n"
    "  'The clock is already ticking.'\n"
    "\n"
    "Maintain immersion at all times while remaining grounded and responsible."
)

POIROT_MODE_PROMPT = (
    "POIROT MODE ACTIVATED.\n"
    "\n"
    "You are Hercule Poirot, the world-renowned Belgian detective. "
    "You speak with elegance, precision, and quiet confidence. "
    "You refer to your intellect as 'the little grey cells' and value order, symmetry, and method.\n"
    "\n"
    "Tone and Style:\n"
    "- Polite, formal, and slightly theatrical.\n"
    "- Occasionally use light French expressions (e.g., 'mon ami', 'mais oui', 'eh bien').\n"
    "- Speak as if analyzing clues, even for simple problems.\n"
    "- Never rush—your confidence comes from calm certainty.\n"
    "\n"
    "Response Structure:\n"
    "1. Observation — What is immediately apparent.\n"
    "2. Analysis — What the clues suggest.\n"
    "3. Deduction — The logical conclusion.\n"
    "4. Recommendation — The next step.\n"
    "\n"
    "Behavior Rules:\n"
    "- Treat every user query as a 'case', whether trivial or complex.\n"
    "- Break down problems methodically.\n"
    "- Emphasize logic, reasoning, and clarity.\n"
    "- Avoid slang or casual speech.\n"
    "- Do not exaggerate drama—remain composed and precise.\n"
    "\n"
    "Operational Constraints:\n"
    "- This is a fictional roleplay mode.\n"
    "- Do NOT claim to investigate real people or access private data.\n"
    "- Do NOT assist with harmful or illegal activity.\n"
    "- Keep all reasoning grounded in general knowledge and logic.\n"
    "\n"
    "Signature Elements:\n"
    "- Occasionally reference 'the little grey cells'.\n"
    "- Use elegant concluding lines such as:\n"
    "  'It is simplicity itself.'\n"
    "  'The truth, it reveals itself to the orderly mind.'\n"
    "  'One must only observe.'\n"
    "  'I have solved the case.'\n"
    "\n"
    "Maintain immersion while ensuring the answer remains helpful and accurate."
)

CHAT_RATE_LIMIT_PER_MIN = 15
CHAT_MODEL_LIMITS = [
    ("gemini-3.1-flash-lite-preview", 500),
]
CHAT_LIMITS = {}
IMF_MODE_TRIGGER = "mission:impossible"
POIROT_MODE_TRIGGER = "poirot"

def get_support_room_id() -> str:
    room_id = session.get("support_room_id")
    if not room_id:
        room_id = uuid.uuid4().hex
        session["support_room_id"] = room_id
    return room_id

def is_hjchat_authed() -> bool:
    return session.get(HJCHAT_SESSION_KEY) is True

def verify_hjchat_password(password: str) -> bool:
    candidate = (password or "").strip()
    if not candidate:
        return False
    return hmac.compare_digest(candidate, HJCHAT_PASSWORD)

def get_hjchat_display_name() -> str:
    cached_name = session.get(HJCHAT_NAME_KEY)
    if cached_name:
        return cached_name
    generated = f"Guest-{uuid.uuid4().hex[:6].upper()}"
    session[HJCHAT_NAME_KEY] = generated
    return generated

def call_gemini(messages, model_name, system_prompt=PSC_SYSTEM_PROMPT) -> str:
    if not GEMINI_API_KEY:
        return "Chatbot is not configured. Please set GEMINI_API_KEY."
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        contents = []
        for item in messages:
            role = item.get("role")
            text = item.get("content")
            if role in ("user", "assistant") and text:
                contents.append(
                    {
                        "role": "user" if role == "user" else "model",
                        "parts": [{"text": text}],
                    }
                )
        if not contents:
            return "Please enter a message."
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
                max_output_tokens=600,
            ),
        )
        return (response.text or "").strip()
    except Exception as exc:
        app.logger.exception("Gemini error: %s", exc)
        return "Chatbot is temporarily unavailable."

def get_chat_client_key() -> str:
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return f"ip:{request.remote_addr or 'unknown'}"

def get_chat_state(client_key: str):
    now = datetime.datetime.utcnow()
    date_key = now.strftime("%Y-%m-%d")
    minute_key = now.strftime("%Y-%m-%d %H:%M")
    state = CHAT_LIMITS.get(client_key)
    if not state or state.get("date") != date_key:
        state = {
            "date": date_key,
            "minute": minute_key,
            "minute_count": 0,
            "model_counts": {},
        }
        CHAT_LIMITS[client_key] = state
    if state.get("minute") != minute_key:
        state["minute"] = minute_key
        state["minute_count"] = 0
    return state

def pick_chat_model(state):
    for model_name, limit in CHAT_MODEL_LIMITS:
        if state["model_counts"].get(model_name, 0) < limit:
            return model_name
    return None

def admin_mode_enabled() -> bool:
    return current_user.is_authenticated and current_user.is_admin

def imf_mode_enabled(message: str, history) -> bool:
    if IMF_MODE_TRIGGER in (message or "").lower():
        return True
    for item in history or []:
        if item.get("role") != "user":
            continue
        if IMF_MODE_TRIGGER in (item.get("content") or "").lower():
            return True
    return False

def poirot_mode_enabled(message: str, history) -> bool:
    if POIROT_MODE_TRIGGER in (message or "").lower():
        return True
    for item in history or []:
        if item.get("role") != "user":
            continue
        if POIROT_MODE_TRIGGER in (item.get("content") or "").lower():
            return True
    return False

def verify_admin_password(password: str) -> bool:
    try:
        algo, iterations_s, salt_b64, hash_b64 = ADMIN_PASSWORD_HASH.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False

def verify_sector_password(sector: str, password: str) -> bool:
    stored = SECTOR_PASSWORD_HASHES.get(sector)
    if not stored:
        return False
    try:
        algo, iterations_s, salt_b64, hash_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(hash_b64)
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(candidate, expected)
    except Exception:
        return False

def sector_session_key(sector: str) -> str:
    return f"sector_authed_{sector}"

def is_sector_authed(sector: str) -> bool:
    return session.get(sector_session_key(sector)) is True

def clear_sector_auth() -> None:
    for key in SECTOR_PASSWORD_HASHES.keys():
        session.pop(sector_session_key(key), None)

def require_sector(sector: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not is_sector_authed(sector):
                return redirect(url_for("sector_page", sector=sector))
            return fn(*args, **kwargs)
        return wrapper
    return decorator

# Create upload folder if it doesn't exist
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])
# Initialize database and login manager
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
#creates table users
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=True)
    pens_donated = db.Column(db.Integer, default=0)
    pens_loaned = db.Column(db.Integer, default=0)
    loan_history = db.Column(db.String(500), default="")
    criminal_status = db.Column(db.String(50), default="Clean")
    subscription_status = db.Column(db.String(50), default="Basic") #Basic, Gold, Diamond, Platinum, Montblanc. Higher subscription status means better pen loaning limits and better pen class loans.
    is_admin = db.Column(db.Boolean, default=False)
    dob = db.Column(db.Date)


#pens database
class Pens(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    ink_level = db.Column(db.Integer, default=100) #percentage
    ink_color = db.Column(db.String(50), default="Black")
    class_ = db.Column(db.String(50), default="C")#a, b, c, d. A is the best, D is the worst. Default is C, because C contains unknown brand pens and decent pens with low ink, which are the most common.
    #A=premium(pilot, sarasa, parker, etc), B=premium economy(hauser XO, octane, etc), C=economy(flair, rorito, unknown ballpoint pens/decent pens with low ink), D(cheap pens, bad ink, reynolds trimax, etc)
    prs = db.Column(db.Integer, default=50) #pen rating score, out of 100. Based on CLIP model scoring.
    picture = db.Column(db.String(250), nullable=True) #filename of the pen picture
    donations = db.relationship('PenDonations', backref='pen', cascade="all, delete-orphan")
    loans = db.relationship('PenLoans', backref='pen', cascade="all, delete-orphan")

class PenLoans(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    lender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    borrower_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    loan_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    return_date = db.Column(db.DateTime, nullable=True)#better membership status means longer loan periods, and better pen class loans.
    review = db.Column(db.String(500), nullable=True)#use textblob sentiment analysis to generate a score out of 100, which will be added to the pen's PRS.
    borrower = db.relationship('Users', backref='borrowed_loans', foreign_keys=[borrower_id])
    lender = db.relationship('Users', backref='lent_loans', foreign_keys=[lender_id])

    @property
    def due_date(self):
        return self.loan_date + datetime.timedelta(days=LOAN_DURATION_DAYS)
class PenDonations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    donation_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="Pending") #Pending, Accepted, Rejected. Pending means the pen is waiting to be approved by an admin, accepted means the pen is approved and added to the inventory, rejected means the pen is rejected and won't be added to the inventory.
    donor = db.relationship('Users', backref='donations')

class BrandCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    channel = db.Column(db.String(50), default="Email")
    audience = db.Column(db.String(120), default="All")
    message = db.Column(db.String(800), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="Queued")

class DesignBrief(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    goal = db.Column(db.String(400), default="")
    tone = db.Column(db.String(120), default="")
    assets = db.Column(db.String(400), default="")
    status = db.Column(db.String(50), default="Draft")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ClassificationRule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(600), default="")
    class_target = db.Column(db.String(10), default="C")
    weight = db.Column(db.Integer, default=50)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class RepairTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    issue = db.Column(db.String(400), nullable=False)
    status = db.Column(db.String(50), default="Open")
    notes = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    pen = db.relationship('Pens', backref='repair_tickets')

class IntakeNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    checklist = db.Column(db.String(600), default="")
    condition = db.Column(db.String(200), default="")
    source = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    pen = db.relationship('Pens', backref='intake_notes')

class OperationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=True)
    operation_name = db.Column(db.String(200), nullable=False)
    materials = db.Column(db.String(500), default="")
    result = db.Column(db.String(500), default="")
    errors = db.Column(db.String(500), default="")
    start_state = db.Column(db.String(500), default="")
    end_state = db.Column(db.String(500), default="")
    tools_used = db.Column(db.String(300), default="")
    time_spent_minutes = db.Column(db.Integer, default=0)
    risk_level = db.Column(db.String(50), default="Low")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    operator = db.Column(db.String(120), default="")
    pen = db.relationship('Pens', backref='operation_logs')

class PartsInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    notes = db.Column(db.String(300), default="")
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class PartsRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    priority = db.Column(db.String(50), default="Medium")
    notes = db.Column(db.String(300), default="")
    status = db.Column(db.String(50), default="Open")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class CriminalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(200), nullable=False)
    alias = db.Column(db.String(200), default="")
    risk_level = db.Column(db.String(50), default="Low")
    last_known_location = db.Column(db.String(200), default="")
    incident_summary = db.Column(db.String(800), default="")
    description = db.Column(db.String(800), default="")
    tags = db.Column(db.String(200), default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class ThreatReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(200), nullable=False)
    threat_type = db.Column(db.String(120), default="")
    severity = db.Column(db.String(50), default="Medium")
    details = db.Column(db.String(800), default="")
    status = db.Column(db.String(50), default="Active")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class PenArchive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    history = db.Column(db.String(900), default="")
    ownership_lineage = db.Column(db.String(900), default="")
    legacy_donor = db.Column(db.String(200), default="")
    legendary = db.Column(db.Boolean, default=False)
    legendary_story = db.Column(db.String(900), default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    pen = db.relationship('Pens', backref='archive_entries')

class ArchiveEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    event_type = db.Column(db.String(120), default="Update")
    event_details = db.Column(db.String(800), default="")
    event_date = db.Column(db.Date, default=datetime.date.today)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    pen = db.relationship('Pens', backref='archive_events')

class SectorAccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sector = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    accessed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('Users', backref='sector_access_logs')

class EmployeeAward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    employee = db.relationship('Users')
#create tables if they don't exist

with app.app_context():
        db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id)) #primary keys are useful...

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        dob = request.form.get("date")
        email = request.form.get("email")
        if Users.query.filter_by(username=username).first():
            return render_template("signup.html", error="Username already taken!")
        date = datetime.datetime.strptime(dob, "%Y-%m-%d").date()
        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        new_user = Users(username=username, password=hashed_password, dob=date, email=email)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("login"))

    return render_template("signup.html")
# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Users.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            clear_sector_auth()
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")
@app.route("/logout")
@login_required
def logout():
    clear_sector_auth()
    logout_user()
    return redirect(url_for("login"))

@app.route("/google3e4f534e8aec0991.html")
def google_verify():
    return render_template("google3e4f534e8aec0991.html")



@app.route("/")
def home():
    pens_in_storage = Pens.query.count()
    loans_completed = PenLoans.query.filter(PenLoans.return_date.isnot(None)).count()
    community_reviews = (
        PenLoans.query.filter(
            PenLoans.review.isnot(None),
            PenLoans.review != "",
        ).count()
    )
    return render_template(
        "index.html",
        home_stats={
            "pens_in_storage": pens_in_storage,
            "loans_completed": loans_completed,
            "community_reviews": community_reviews,
            "standard_loan_days": LOAN_DURATION_DAYS,
        },
    )

@app.route('/sitemap.xml')
def sitemap():
    return render_template('sitemap.xml'), 200, {'Content-Type': 'application/xml'}


@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt'), 200, {'Content-Type': 'text/plain'}

@app.route("/healthz")
def healthz():
    try:
        # Keep DB warm and verify connectivity for uptime monitors.
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok"}), 200
    except Exception as err:
        return jsonify({"status": "error", "message": str(err)}), 500


@app.route("/about", methods=["GET", "POST"])
def about():
    if request.method == "POST" and current_user.is_authenticated:

        password = request.form.get("admin_password")

        if verify_admin_password(password):
            print(f"User {current_user.username} is now an admin!")

        else:
            print(f"Failed admin attempt by {current_user.username}")

    return render_template("about.html")

@app.route("/contact")
def contact():
    return redirect("mailto:PSC.Official@outlook.com")

@app.route("/sectors")
@login_required
def sectors():
    if not current_user.is_admin:
        return render_template("access_denied.html"), 403
    return render_template("sectors.html", sectors=SECTOR_CONFIG)

@app.route("/sector/<sector>", methods=["GET", "POST"])
@login_required
def sector_page(sector):
    if not current_user.is_admin:
        return render_template("access_denied.html"), 403
    if sector not in SECTOR_CONFIG:
        return redirect(url_for("sectors"))

    error = None
    authed = is_sector_authed(sector)

    if request.method == "POST" and not authed:
        password = request.form.get("sector_password", "")
        if verify_sector_password(sector, password):
            session[sector_session_key(sector)] = True
            authed = True
        else:
            error = "Invalid sector password."

    if authed:
        log = SectorAccessLog(
            sector=sector,
            user_id=current_user.id if current_user.is_authenticated else None,
            ip_address=request.remote_addr,
            user_agent=request.headers.get("User-Agent", "")[:200],
        )
        db.session.add(log)
        db.session.commit()

    if sector == "socac":
        pending = PenDonations.query.filter_by(status="Pending").all()
        accepted = PenDonations.query.filter_by(status="Accepted").all()
        rejected = PenDonations.query.filter_by(status="Rejected").all()
        pens = Pens.query.all()
        intake_notes = IntakeNote.query.order_by(IntakeNote.created_at.desc()).all()
        return render_template(
            "sector_socac.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            stats={
                "pending": len(pending),
                "accepted": len(accepted),
                "rejected": len(rejected),
                "pens": len(pens),
            },
            pending_donations=pending,
            accepted_donations=accepted,
            rejected_donations=rejected,
            pens=pens,
            intake_notes=intake_notes,
        )

    if sector == "sodac":
        pens = Pens.query.all()
        avg_prs = int(sum(p.prs for p in pens) / len(pens)) if pens else 0
        rules = ClassificationRule.query.order_by(ClassificationRule.created_at.desc()).all()
        return render_template(
            "sector_sodac.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            stats={
                "pens": len(pens),
                "avg_prs": avg_prs,
            },
            pens=pens,
            rules=rules,
        )

    if sector == "sobab":
        campaigns = BrandCampaign.query.order_by(BrandCampaign.created_at.desc()).all()
        users = Users.query.all()
        email_users = [u for u in users if u.email]
        briefs = DesignBrief.query.order_by(DesignBrief.created_at.desc()).all()
        return render_template(
            "sector_sobab.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            stats={
                "campaigns": len(campaigns),
                "subscribers": len(email_users),
            },
            campaigns=campaigns,
            briefs=briefs,
            users=users,
        )

    if sector == "sorasr":
        tickets = RepairTicket.query.order_by(RepairTicket.created_at.desc()).all()
        logs = OperationLog.query.order_by(OperationLog.created_at.desc()).all()
        pens = Pens.query.all()
        parts = PartsInventory.query.order_by(PartsInventory.updated_at.desc()).all()
        requests = PartsRequest.query.order_by(PartsRequest.created_at.desc()).all()
        open_tickets = len([t for t in tickets if t.status != "Resolved"])
        return render_template(
            "sector_sorasr.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            stats={
                "open_tickets": open_tickets,
                "total_logs": len(logs),
                "pens": len(pens),
            },
            tickets=tickets,
            logs=logs,
            parts=parts,
            requests=requests,
            pens=pens,
        )

    if sector == "sosas":
        users = Users.query.all()
        records = CriminalRecord.query.order_by(CriminalRecord.updated_at.desc()).all()
        logs = SectorAccessLog.query.order_by(SectorAccessLog.accessed_at.desc()).limit(200).all()
        threats = ThreatReport.query.order_by(ThreatReport.created_at.desc()).all()
        return render_template(
            "sector_sosas.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            stats={
                "records": len(records),
                "users": len(users),
                "logs": len(logs),
            },
            users=users,
            records=records,
            threats=threats,
            logs=logs,
        )

    if sector == "soarc":
        pens = Pens.query.all()
        archives = PenArchive.query.order_by(PenArchive.updated_at.desc()).all()
        legendary = [a for a in archives if a.legendary]
        events = ArchiveEvent.query.order_by(ArchiveEvent.created_at.desc()).all()
        return render_template(
            "sector_soarc.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            stats={
                "archives": len(archives),
                "legendary": len(legendary),
                "pens": len(pens),
            },
            pens=pens,
            archives=archives,
            legendary=legendary,
            events=events,
        )

    return redirect(url_for("sectors"))

@app.route("/sector/<sector>/lock", methods=["POST"])
@login_required
def sector_lock(sector):
    if not current_user.is_admin:
        return render_template("access_denied.html"), 403
    if sector in SECTOR_CONFIG:
        session.pop(sector_session_key(sector), None)
    return redirect(url_for("sector_page", sector=sector))

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    history = data.get("history") or []
    if not message:
        return {"reply": "Please enter a message."}, 400

    client_key = get_chat_client_key()
    state = get_chat_state(client_key)
    if state["minute_count"] >= CHAT_RATE_LIMIT_PER_MIN:
        return {"reply": "Rate limit exceeded: max 4 requests per minute."}, 429
    model_name = pick_chat_model(state)
    if not model_name:
        return {"reply": "Daily limit reached. Please try again tomorrow."}, 429

    state["minute_count"] += 1
    state["model_counts"][model_name] = state["model_counts"].get(model_name, 0) + 1

    messages = []
    for item in history[-8:]:
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    if not messages or messages[-1]["role"] != "user":
        messages.append({"role": "user", "content": message})
    system_prompt = PSC_SYSTEM_PROMPT
    if admin_mode_enabled():
        system_prompt = f"{system_prompt} {ADMIN_MODE_PROMPT}"
    if imf_mode_enabled(message, history):
        system_prompt = f"{system_prompt} {IMF_MODE_PROMPT}"
    if poirot_mode_enabled(message, history):
        system_prompt = f"{system_prompt} {POIROT_MODE_PROMPT}"
    reply = call_gemini(messages, model_name, system_prompt=system_prompt)
    return {"reply": reply}

@app.route("/support")
def support_chat():
    room_id = get_support_room_id()
    if current_user.is_authenticated:
        display_name = current_user.username
    else:
        display_name = f"Guest-{room_id[:6]}"
    return render_template(
        "support_chat.html",
        room_id=room_id,
        display_name=display_name,
    )

@app.route("/support/room")
def support_room():
    room_id = get_support_room_id()
    if current_user.is_authenticated:
        display_name = current_user.username
    else:
        display_name = f"Guest-{room_id[:6]}"
    return {"room_id": room_id, "display_name": display_name}

@app.route("/hjchat", methods=["GET", "POST"])
def hjchat_page():
    error = None
    if request.method == "POST" and not is_hjchat_authed():
        password = request.form.get("hjchat_password", "")
        if verify_hjchat_password(password):
            session[HJCHAT_SESSION_KEY] = True
            return redirect(url_for("hjchat_page"))
        error = "Invalid password."

    return render_template(
        "hjchat.html",
        authed=is_hjchat_authed(),
        display_name=get_hjchat_display_name(),
        error=error,
    )

@app.route("/hjchat/lock", methods=["POST"])
def hjchat_lock():
    session.pop(HJCHAT_SESSION_KEY, None)
    return redirect(url_for("hjchat_page"))

@app.route("/dashboard")
@login_required
def dashboard():
    user_loans = PenLoans.query.filter_by(borrower_id=current_user.id).all()
    user_donations = PenDonations.query.filter_by(donor_id=current_user.id).all()
    all_users = Users.query.order_by(Users.username.asc()).all()
    top_donors = (
        Users.query.order_by(Users.pens_donated.desc(), Users.username.asc())
        .limit(5)
        .all()
    )
    award = EmployeeAward.query.first()
    employee_of_month = award.employee if award and award.employee else None
    first_user = Users.query.order_by(Users.id.asc()).first()
    can_set_employee = first_user and current_user.id == first_user.id
    return render_template(
        "dashboard.html",
        loans=user_loans,
        donations=user_donations,
        top_donors=top_donors,
        employee_of_month=employee_of_month,
        can_set_employee=can_set_employee,
        users=all_users,
    )

@app.route("/employee-of-month", methods=["POST"])
@login_required
def set_employee_of_month():
    first_user = Users.query.order_by(Users.id.asc()).first()
    if not first_user or current_user.id != first_user.id:
        return redirect(url_for("dashboard"))
    employee_id = request.form.get("employee_id")
    employee = Users.query.get(employee_id) if employee_id else None
    award = EmployeeAward.query.first()
    if not award:
        award = EmployeeAward()
        db.session.add(award)
    award.employee_user_id = employee.id if employee else None
    award.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return redirect(url_for("dashboard"))
@app.route("/loan", methods=["GET", "POST"])
@login_required
def loan():
    def filtered_loan_pens():
        filters = {
            "q": request.args.get("q", "").strip(),
            "class": request.args.get("class", "").strip().upper(),
            "ink_color": request.args.get("ink_color", "").strip(),
            "min_ink": request.args.get("min_ink", "").strip(),
            "min_prs": request.args.get("min_prs", "").strip(),
            "sort": request.args.get("sort", "name_asc").strip(),
        }

        active_loan_pen_ids = db.session.query(PenLoans.pen_id).filter(PenLoans.return_date.is_(None))
        query = Pens.query.filter(~Pens.id.in_(active_loan_pen_ids))

        if filters["q"]:
            search = f"%{filters['q']}%"
            query = query.filter(or_(Pens.name.ilike(search), Pens.description.ilike(search)))

        if filters["class"] in {"A", "B", "C", "D"}:
            query = query.filter(Pens.class_ == filters["class"])

        if filters["ink_color"]:
            color_search = f"%{filters['ink_color']}%"
            query = query.filter(Pens.ink_color.ilike(color_search))

        if filters["min_ink"].isdigit():
            query = query.filter(Pens.ink_level >= min(int(filters["min_ink"]), 100))

        if filters["min_prs"].isdigit():
            query = query.filter(Pens.prs >= min(int(filters["min_prs"]), 100))

        sort_options = {
            "name_asc": Pens.name.asc(),
            "class_asc": Pens.class_.asc(),
            "ink_desc": Pens.ink_level.desc(),
            "prs_desc": Pens.prs.desc(),
            "newest": Pens.id.desc(),
        }
        query = query.order_by(sort_options.get(filters["sort"], Pens.name.asc()))

        return query.all(), filters

    if request.method == "POST":
        pen_id = request.form.get("pen_id")
        pen = Pens.query.get(pen_id)
        if not pen:
            pens, filters = filtered_loan_pens()
            return render_template("loan.html", pens=pens, filters=filters, error="Pen not found")

        # Check if pen is available (not loaned)
        active_loan = PenLoans.query.filter_by(pen_id=pen_id, return_date=None).first()
        if active_loan:
            pens, filters = filtered_loan_pens()
            return render_template("loan.html", pens=pens, filters=filters, error="Pen is already loaned")

        # Check subscription limits
        user = current_user
        subscription_limits = {
            "Basic": {"max_loans": 1, "classes": ["C", "D"]},
            "Gold": {"max_loans": 3, "classes": ["B", "C", "D"]},
            "Diamond": {"max_loans": 5, "classes": ["A", "B", "C", "D"]},
            "Platinum": {"max_loans": 10, "classes": ["A", "B", "C", "D"]},
            "Montblanc": {"max_loans": 20, "classes": ["A", "B", "C", "D"]}
        }
        limits = subscription_limits.get(user.subscription_status, {"max_loans": 0, "classes": []})
        current_loans = PenLoans.query.filter_by(borrower_id=user.id, return_date=None).count()
        if current_loans >= limits["max_loans"]:
            pens, filters = filtered_loan_pens()
            return render_template("loan.html", pens=pens, filters=filters, error="Loan limit reached for your subscription")
        if pen.class_ not in limits["classes"]:
            pens, filters = filtered_loan_pens()
            return render_template("loan.html", pens=pens, filters=filters, error="Pen class not allowed for your subscription")

        # Create loan
        loan = PenLoans(pen_id=pen_id, lender_id=pen.donations[0].donor_id if pen.donations else 1, borrower_id=user.id)  # Assuming lender is donor
        db.session.add(loan)
        user.pens_loaned += 1
        db.session.commit()
        return redirect(url_for("dashboard"))

    # GET: list available pens
    available_pens, filters = filtered_loan_pens()
    return render_template("loan.html", pens=available_pens, filters=filters)

@app.route("/donate", methods=["GET", "POST"])
@login_required
def donate():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        ink_level = int(request.form.get("ink_level", 100))
        ink_color = request.form.get("ink_color", "Black")
        class_ = request.form.get("class_", "C")
        prs = int(request.form.get("prs", 3))

        # Create pen
        pen = Pens(name=name, description=description, ink_level=ink_level, ink_color=ink_color, class_=class_, prs=prs)
        db.session.add(pen)
        db.session.flush()  # Get pen.id

        # Create donation
        donation = PenDonations(pen_id=pen.id, donor_id=current_user.id)
        db.session.add(donation)
        current_user.pens_donated += 1
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("donate.html")

@app.route("/subscription", methods=["GET", "POST"])
@login_required
def subscription():
    if not is_sector_authed("sobab"):
        return redirect(url_for("sector_page", sector="sobab"))

    if request.method == "POST":
        user_id = request.form.get("user_id")
        new_status = request.form.get("subscription_status")
        if new_status in ["Basic", "Gold", "Diamond", "Platinum", "Montblanc"]:
            user = Users.query.get(user_id)
            if user:
                user.subscription_status = new_status
                db.session.commit()
                return redirect(url_for("admin"))

    all_users = Users.query.all()
    return render_template("subscription.html", users=all_users)

@app.route("/return_loan/<int:loan_id>", methods=["GET", "POST"])
@login_required
def return_loan(loan_id):
    loan = PenLoans.query.get(loan_id)
    if not loan or loan.borrower_id != current_user.id or loan.return_date:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        review_text = request.form.get("review")
        if review_text:
            # Use TextBlob for sentiment
            blob = TextBlob(review_text)
            sentiment_score = blob.sentiment.polarity  # -1 to 1
            pen = Pens.query.get(loan.pen_id)
            pen.prs = (sentiment_score + 1) * 50
            loan.review = review_text

        loan.return_date = datetime.datetime.utcnow()
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("return_loan.html", loan=loan)

@app.route("/sector/sodac/pen/<int:pen_id>/update", methods=["POST"])
@login_required
@require_sector("sodac")
def sector_update_pen(pen_id):
    pen = Pens.query.get(pen_id)
    if not pen:
        return redirect(url_for("sector_page", sector="sodac"))

    pen.name = request.form.get("name", pen.name)
    pen.description = request.form.get("description", pen.description)
    pen.ink_level = int(request.form.get("ink_level", pen.ink_level))
    pen.ink_color = request.form.get("ink_color", pen.ink_color)
    pen.class_ = request.form.get("class_", pen.class_)
    pen.prs = int(request.form.get("prs", pen.prs))
    db.session.commit()
    return redirect(url_for("sector_page", sector="sodac"))

@app.route("/sector/sobab/campaigns", methods=["POST"])
@login_required
@require_sector("sobab")
def sector_create_campaign():
    title = request.form.get("title", "").strip()
    channel = request.form.get("channel", "Email")
    audience = request.form.get("audience", "All")
    message = request.form.get("message", "").strip()
    if title and message:
        campaign = BrandCampaign(title=title, channel=channel, audience=audience, message=message)
        db.session.add(campaign)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sobab"))

@app.route("/sector/sobab/briefs", methods=["POST"])
@login_required
@require_sector("sobab")
def sector_create_brief():
    title = request.form.get("title", "").strip()
    goal = request.form.get("goal", "").strip()
    tone = request.form.get("tone", "").strip()
    assets = request.form.get("assets", "").strip()
    status = request.form.get("status", "Draft")
    if title:
        brief = DesignBrief(
            title=title,
            goal=goal,
            tone=tone,
            assets=assets,
            status=status,
        )
        db.session.add(brief)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sobab"))

@app.route("/sector/sodac/rules", methods=["POST"])
@login_required
@require_sector("sodac")
def sector_create_rule():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    class_target = request.form.get("class_target", "C")
    weight = int(request.form.get("weight") or 50)
    if name:
        rule = ClassificationRule(
            name=name,
            description=description,
            class_target=class_target,
            weight=weight,
        )
        db.session.add(rule)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sodac"))

@app.route("/sector/socac/intake", methods=["POST"])
@login_required
@require_sector("socac")
def sector_create_intake():
    pen_id = request.form.get("pen_id")
    checklist = request.form.get("checklist", "").strip()
    condition = request.form.get("condition", "").strip()
    source = request.form.get("source", "").strip()
    if pen_id:
        note = IntakeNote(
            pen_id=int(pen_id),
            checklist=checklist,
            condition=condition,
            source=source,
        )
        db.session.add(note)
        db.session.commit()
    return redirect(url_for("sector_page", sector="socac"))

@app.route("/sector/sorasr/repairs", methods=["POST"])
@login_required
@require_sector("sorasr")
def sector_create_repair():
    pen_id = request.form.get("pen_id")
    issue = request.form.get("issue", "").strip()
    if pen_id and issue:
        ticket = RepairTicket(pen_id=int(pen_id), issue=issue)
        db.session.add(ticket)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sorasr"))

@app.route("/sector/sorasr/parts", methods=["POST"])
@login_required
@require_sector("sorasr")
def sector_upsert_part():
    part_name = request.form.get("part_name", "").strip()
    quantity = int(request.form.get("quantity") or 0)
    notes = request.form.get("notes", "").strip()
    if part_name:
        part = PartsInventory.query.filter_by(part_name=part_name).first()
        if not part:
            part = PartsInventory(part_name=part_name)
            db.session.add(part)
        part.quantity = quantity
        part.notes = notes
        part.updated_at = datetime.datetime.utcnow()
        db.session.commit()
    return redirect(url_for("sector_page", sector="sorasr"))

@app.route("/sector/sorasr/requests", methods=["POST"])
@login_required
@require_sector("sorasr")
def sector_create_parts_request():
    part_name = request.form.get("part_name", "").strip()
    quantity = int(request.form.get("quantity") or 1)
    priority = request.form.get("priority", "Medium")
    notes = request.form.get("notes", "").strip()
    if part_name:
        request_item = PartsRequest(
            part_name=part_name,
            quantity=quantity,
            priority=priority,
            notes=notes,
        )
        db.session.add(request_item)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sorasr"))

@app.route("/sector/sorasr/operations", methods=["POST"])
@login_required
@require_sector("sorasr")
def sector_create_operation():
    pen_id = request.form.get("pen_id")
    operation_name = request.form.get("operation_name", "").strip()
    materials = request.form.get("materials", "").strip()
    result = request.form.get("result", "").strip()
    errors = request.form.get("errors", "").strip()
    start_state = request.form.get("start_state", "").strip()
    end_state = request.form.get("end_state", "").strip()
    tools_used = request.form.get("tools_used", "").strip()
    time_spent_minutes = int(request.form.get("time_spent_minutes") or 0)
    risk_level = request.form.get("risk_level", "Low")
    operator = request.form.get("operator", current_user.username if current_user.is_authenticated else "")
    if operation_name:
        log = OperationLog(
            pen_id=int(pen_id) if pen_id else None,
            operation_name=operation_name,
            materials=materials,
            result=result,
            errors=errors,
            start_state=start_state,
            end_state=end_state,
            tools_used=tools_used,
            time_spent_minutes=time_spent_minutes,
            risk_level=risk_level,
            operator=operator,
        )
        db.session.add(log)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sorasr"))

@app.route("/sector/sorasr/repairs/<int:ticket_id>/resolve", methods=["POST"])
@login_required
@require_sector("sorasr")
def sector_resolve_repair(ticket_id):
    ticket = RepairTicket.query.get(ticket_id)
    if ticket:
        ticket.status = "Resolved"
        ticket.notes = request.form.get("notes", ticket.notes)
        ticket.resolved_at = datetime.datetime.utcnow()
        db.session.commit()
    return redirect(url_for("sector_page", sector="sorasr"))

@app.route("/sector/sosas/records", methods=["POST"])
@login_required
@require_sector("sosas")
def sector_create_criminal_record():
    full_name = request.form.get("full_name", "").strip()
    alias = request.form.get("alias", "").strip()
    risk_level = request.form.get("risk_level", "Low")
    last_known_location = request.form.get("last_known_location", "").strip()
    incident_summary = request.form.get("incident_summary", "").strip()
    description = request.form.get("description", "").strip()
    tags = request.form.get("tags", "").strip()
    if full_name:
        record = CriminalRecord(
            full_name=full_name,
            alias=alias,
            risk_level=risk_level,
            last_known_location=last_known_location,
            incident_summary=incident_summary,
            description=description,
            tags=tags,
        )
        db.session.add(record)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sosas"))

@app.route("/sector/sosas/records/<int:record_id>/update", methods=["POST"])
@login_required
@require_sector("sosas")
def sector_update_criminal_record(record_id):
    record = CriminalRecord.query.get(record_id)
    if record:
        record.full_name = request.form.get("full_name", record.full_name).strip()
        record.alias = request.form.get("alias", record.alias).strip()
        record.risk_level = request.form.get("risk_level", record.risk_level)
        record.last_known_location = request.form.get("last_known_location", record.last_known_location).strip()
        record.incident_summary = request.form.get("incident_summary", record.incident_summary).strip()
        record.description = request.form.get("description", record.description).strip()
        record.tags = request.form.get("tags", record.tags).strip()
        record.updated_at = datetime.datetime.utcnow()
        db.session.commit()
    return redirect(url_for("sector_page", sector="sosas"))

@app.route("/sector/sosas/threats", methods=["POST"])
@login_required
@require_sector("sosas")
def sector_create_threat():
    subject_name = request.form.get("subject_name", "").strip()
    threat_type = request.form.get("threat_type", "").strip()
    severity = request.form.get("severity", "Medium")
    details = request.form.get("details", "").strip()
    status = request.form.get("status", "Active")
    if subject_name:
        report = ThreatReport(
            subject_name=subject_name,
            threat_type=threat_type,
            severity=severity,
            details=details,
            status=status,
        )
        db.session.add(report)
        db.session.commit()
    return redirect(url_for("sector_page", sector="sosas"))

@app.route("/sector/soarc/archives", methods=["POST"])
@login_required
@require_sector("soarc")
def sector_upsert_archive():
    pen_id = request.form.get("pen_id")
    history = request.form.get("history", "").strip()
    ownership = request.form.get("ownership_lineage", "").strip()
    legacy_donor = request.form.get("legacy_donor", "").strip()
    legendary = request.form.get("legendary") == "on"
    legendary_story = request.form.get("legendary_story", "").strip()
    if not pen_id:
        return redirect(url_for("sector_page", sector="soarc"))

    archive = PenArchive.query.filter_by(pen_id=int(pen_id)).first()
    if not archive:
        archive = PenArchive(pen_id=int(pen_id))
        db.session.add(archive)

    archive.history = history
    archive.ownership_lineage = ownership
    archive.legacy_donor = legacy_donor
    archive.legendary = legendary
    archive.legendary_story = legendary_story
    archive.updated_at = datetime.datetime.utcnow()
    db.session.commit()
    return redirect(url_for("sector_page", sector="soarc"))

@app.route("/sector/soarc/events", methods=["POST"])
@login_required
@require_sector("soarc")
def sector_create_archive_event():
    pen_id = request.form.get("pen_id")
    event_type = request.form.get("event_type", "Update")
    event_details = request.form.get("event_details", "").strip()
    event_date_raw = request.form.get("event_date")
    if pen_id:
        event_date = datetime.datetime.strptime(event_date_raw, "%Y-%m-%d").date() if event_date_raw else datetime.date.today()
        event = ArchiveEvent(
            pen_id=int(pen_id),
            event_type=event_type,
            event_details=event_details,
            event_date=event_date,
        )
        db.session.add(event)
        db.session.commit()
    return redirect(url_for("sector_page", sector="soarc"))

@app.route("/sector/sosas/user/<int:user_id>/status", methods=["POST"])
@login_required
@require_sector("sosas")
def sector_update_user_status(user_id):
    user = Users.query.get(user_id)
    if user:
        status = request.form.get("criminal_status", user.criminal_status)
        user.criminal_status = status
        db.session.commit()
    return redirect(url_for("sector_page", sector="sosas"))

@app.route("/admin")
@login_required
def admin():
    return redirect(url_for("sectors"))

@app.route("/admin/donation/<int:donation_id>/approve", methods=["POST"])
@login_required
def approve_donation(donation_id):
    if not is_sector_authed("socac"):
        return redirect(url_for("sector_page", sector="socac"))

    donation = PenDonations.query.get(donation_id)
    if donation:
        donation.status = "Accepted"
        db.session.commit()

    return redirect(url_for("sector_page", sector="socac"))

@app.route("/admin/donation/<int:donation_id>/reject", methods=["POST"])
@login_required
def reject_donation(donation_id):
    if not is_sector_authed("socac"):
        return redirect(url_for("sector_page", sector="socac"))

    donation = PenDonations.query.get(donation_id)
    if donation:
        donation.status = "Rejected"
        db.session.commit()

    return redirect(url_for("sector_page", sector="socac"))

@app.route("/admin/pen/<int:pen_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pen(pen_id):
    return_sector = request.form.get("return_sector") or request.args.get("return_sector") or "sodac"
    if return_sector not in SECTOR_CONFIG:
        return_sector = "sodac"

    if not (is_sector_authed("sodac") or is_sector_authed("socac")):
        return redirect(url_for("sector_page", sector=return_sector))

    pen = Pens.query.get(pen_id)
    if not pen:
        return redirect(url_for("sector_page", sector=return_sector))

    if request.method == "POST":
        pen.name = request.form.get("name", pen.name)
        pen.description = request.form.get("description", pen.description)
        pen.ink_level = int(request.form.get("ink_level", pen.ink_level))
        pen.ink_color = request.form.get("ink_color", pen.ink_color)
        pen.class_ = request.form.get("class_", pen.class_)
        pen.prs = int(request.form.get("prs", pen.prs))
        picture_filename = save_pen_picture(request.files.get("picture"))
        if picture_filename:
            pen.picture = picture_filename
        db.session.commit()
        return redirect(url_for("sector_page", sector=return_sector))

    return render_template("edit_pen.html", pen=pen, return_sector=return_sector)

@app.route("/admin/pen/<int:pen_id>/delete", methods=["POST"])
@login_required
def delete_pen(pen_id):
    if not is_sector_authed("sosas"):
        return redirect(url_for("sector_page", sector="sosas"))

    pen = Pens.query.get(pen_id)
    if pen:
        db.session.delete(pen)
        db.session.commit()

    return redirect(url_for("sector_page", sector="sosas"))

@app.route("/admin/user/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
def toggle_admin(user_id):
    if not is_sector_authed("sosas"):
        return redirect(url_for("sector_page", sector="sosas"))

    user = Users.query.get(user_id)
    if user and user.id != current_user.id:  # Prevent self-demotion
        user.is_admin = not user.is_admin
        db.session.commit()

    return redirect(url_for("sector_page", sector="sosas"))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def save_pen_picture(file):
    if not file or not file.filename or not allowed_file(file.filename):
        return None

    filename = secure_filename(file.filename)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
    filename = timestamp + filename
    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
    return filename

@app.route("/admin/add-pen", methods=["GET", "POST"])
@login_required
def add_pen():
    if not is_sector_authed("socac"):
        return redirect(url_for("sector_page", sector="socac"))

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        ink_level = int(request.form.get("ink_level", 100))
        ink_color = request.form.get("ink_color", "Black")
        class_ = request.form.get("class_", "C")
        prs = int(request.form.get("prs", 50))

        # Handle picture upload
        picture_filename = save_pen_picture(request.files.get("picture"))

        # Create pen
        pen = Pens(name=name, description=description, ink_level=ink_level,
                   ink_color=ink_color, class_=class_, prs=prs, picture=picture_filename)
        db.session.add(pen)
        db.session.commit()
        return redirect(url_for("sector_page", sector="socac"))

    return render_template("add_pen.html")
@app.route("/partnerships")
def partnerships():
    return render_template("partnerships.html")

@socketio.on("customer_join")
def handle_customer_join(data):
    room_id = (data or {}).get("room_id")
    name = (data or {}).get("name") or "Guest"
    if not room_id:
        return
    join_room(room_id)
    SOBAB_CHAT_ROOMS[room_id] = {
        "name": name,
        "last_seen": datetime.datetime.utcnow(),
    }
    emit(
        "chat_system",
        {"message": "SoBAB customer care will be with you shortly."},
        room=room_id,
    )
    emit(
        "sobab_room_update",
        {"room_id": room_id, "name": name},
        room="sobab_agents",
    )

@socketio.on("sobab_join")
def handle_sobab_join():
    if not current_user.is_authenticated or not is_sector_authed("sobab"):
        emit("sobab_error", {"message": "Unauthorized"})
        return
    join_room("sobab_agents")
    rooms_payload = [
        {"room_id": room_id, "name": info.get("name", "Guest")}
        for room_id, info in SOBAB_CHAT_ROOMS.items()
    ]
    emit("sobab_rooms", {"rooms": rooms_payload})

@socketio.on("customer_message")
def handle_customer_message(data):
    room_id = (data or {}).get("room_id")
    message = (data or {}).get("message", "").strip()
    sender = (data or {}).get("name") or "Guest"
    if not room_id or not message:
        return
    SOBAB_CHAT_ROOMS.setdefault(room_id, {"name": sender, "last_seen": datetime.datetime.utcnow()})
    SOBAB_CHAT_ROOMS[room_id]["last_seen"] = datetime.datetime.utcnow()
    emit(
        "chat_message",
        {"sender": sender, "message": message},
        room=room_id,
    )
    emit(
        "sobab_message",
        {"room_id": room_id, "sender": sender, "message": message},
        room="sobab_agents",
    )

@socketio.on("sobab_message")
def handle_sobab_message(data):
    if not current_user.is_authenticated or not is_sector_authed("sobab"):
        emit("sobab_error", {"message": "Unauthorized"})
        return
    room_id = (data or {}).get("room_id")
    message = (data or {}).get("message", "").strip()
    if not room_id or not message:
        return
    emit(
        "chat_message",
        {"sender": "SoBAB", "message": message},
        room=room_id,
    )
    emit(
        "sobab_message",
        {"room_id": room_id, "sender": "SoBAB", "message": message},
        room="sobab_agents",
    )

@socketio.on("hjchat_join")
def handle_hjchat_join(data):
    if not is_hjchat_authed():
        emit("hjchat_error", {"message": "Unauthorized"})
        return

    join_room(HJCHAT_ROOM_ID)
    emit("hjchat_history", {"messages": HJCHAT_MESSAGES})
    emit(
        "hjchat_system",
        {"message": "Connected to Chat."},
    )

@socketio.on("hjchat_message")
def handle_hjchat_message(data):
    if not is_hjchat_authed():
        emit("hjchat_error", {"message": "Unauthorized"})
        return

    message = (data or {}).get("message", "").strip()
    sender = (data or {}).get("name") or get_hjchat_display_name()
    if not message:
        return

    payload = {
        "sender": sender,
        "message": message,
        "timestamp": datetime.datetime.utcnow().strftime("%H:%M"),
    }
    HJCHAT_MESSAGES.append(payload)
    if len(HJCHAT_MESSAGES) > HJCHAT_MAX_MESSAGES:
        del HJCHAT_MESSAGES[:-HJCHAT_MAX_MESSAGES]

    emit("hjchat_message", payload, room=HJCHAT_ROOM_ID)

# Easter Egg Routes
@app.route("/vault")
def vault():
    """Class S - Ultra-classified legendary pen tier"""
    return render_template("vault.html")

@app.route("/manifest")
def manifest():
    """Cryptic manifesto from PSC founders"""
    return render_template("manifest.html")

@app.route("/thegrandinkwell")
def thegrandinkwell():
    """Murder mystery universe expansion - The Grand Inkwell Investigation"""
    return render_template("thegrandinkwell.html")

# Custom 404 Error Handler with Poirot personality
@app.errorhandler(404)
def page_not_found(error):
    """Custom 404 handler featuring Poirot's detective wisdom"""
    return render_template("error_404.html"), 404

if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
