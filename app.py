from flask import Flask, render_template, request, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime
import os
from textblob import TextBlob
import base64
import hashlib
import hmac
from functools import wraps
import smtplib
from email.message import EmailMessage
app = Flask(__name__)
db_uri = "postgresql+psycopg2://database_2fuy_user:JE01RUdze7ABr6h0WhpArvwvqmH2ojee@dpg-d6q3rgsr85hc73bsi5mg-a/database_2fuy"
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
        "pbkdf2_sha256$260000$E0jS2I856uwT6nJ2SSERDg==$EaLeMSyZbBfs9s9qM2VlZhBpGhgWRiiFRO0xLfLLM8M=",
    ),
    "sobab": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOBAB",
        "pbkdf2_sha256$260000$DYnPxO/8p8OPldXffHUAFg==$LS5Aud3yDPgpWIWFtdpLhhJY3l8apQxWRwgx8I/Hp1Q=",
    ),
    "sorasr": os.environ.get(
        "SECTOR_PASSWORD_HASH_SORASR",
        "pbkdf2_sha256$260000$Khnd9VBSzU+Tp2+mSg9HJA==$PDkrCB6IAR33UK/6BYgCyyxkO0MArm1G+wqhuJs+Pl8=",
    ),
    "socac": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOCAC",
        "pbkdf2_sha256$260000$hTKSsgsr1AV52FlcOAbR4g==$mq6H5K97bJjIaPCXkb3lzK+UOv8LVNtUfw22wm/bciE=",
    ),
    "sosas": os.environ.get(
        "SECTOR_PASSWORD_HASH_SOSAS",
        "pbkdf2_sha256$260000$tqgId5Rqpqzwuw1YPFx9mA==$WWeN75bkUI2X5KrAGip4l+jvU0Yao9lc3R8H/aRh030=",
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
}

EMAIL_FROM = os.environ.get("PSC_EMAIL_FROM", "PSC.Official@outlook.com")
EMAIL_PASSWORD = os.environ.get("PSC_EMAIL_PASSWORD", "")
EMAIL_SMTP_HOST = os.environ.get("PSC_EMAIL_SMTP_HOST", "smtp.office365.com")
EMAIL_SMTP_PORT = int(os.environ.get("PSC_EMAIL_SMTP_PORT", "587"))

def send_sector_email(to_address: str, subject: str, body: str) -> None:
    if not EMAIL_PASSWORD:
        return
    msg = EmailMessage()
    msg["From"] = EMAIL_FROM
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)


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
        return self.loan_date + datetime.timedelta(days=7)
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

class RepairTicket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    issue = db.Column(db.String(400), nullable=False)
    status = db.Column(db.String(50), default="Open")
    notes = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    pen = db.relationship('Pens', backref='repair_tickets')

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

class SectorAccessLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sector = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    accessed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('Users', backref='sector_access_logs')
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
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about", methods=["GET", "POST"])
def about():
    if request.method == "POST" and current_user.is_authenticated:

        password = request.form.get("admin_password")

        if verify_admin_password(password):
            current_user.is_admin = True
            db.session.commit()

            print(f"User {current_user.username} is now an admin!")

        else:
            print(f"Failed admin attempt by {current_user.username}")

    return render_template("about.html")

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
        return render_template(
            "sector_socac.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            pending_donations=pending,
            accepted_donations=accepted,
            rejected_donations=rejected,
            pens=pens,
        )

    if sector == "sodac":
        pens = Pens.query.all()
        return render_template(
            "sector_sodac.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            pens=pens,
        )

    if sector == "sobab":
        campaigns = BrandCampaign.query.order_by(BrandCampaign.created_at.desc()).all()
        users = Users.query.all()
        return render_template(
            "sector_sobab.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            campaigns=campaigns,
            users=users,
        )

    if sector == "sorasr":
        tickets = RepairTicket.query.order_by(RepairTicket.created_at.desc()).all()
        logs = OperationLog.query.order_by(OperationLog.created_at.desc()).all()
        pens = Pens.query.all()
        return render_template(
            "sector_sorasr.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            tickets=tickets,
            logs=logs,
            pens=pens,
        )

    if sector == "sosas":
        users = Users.query.all()
        records = CriminalRecord.query.order_by(CriminalRecord.updated_at.desc()).all()
        logs = SectorAccessLog.query.order_by(SectorAccessLog.accessed_at.desc()).limit(200).all()
        return render_template(
            "sector_sosas.html",
            config=SECTOR_CONFIG[sector],
            authed=authed,
            error=error,
            users=users,
            records=records,
            logs=logs,
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

@app.route("/dashboard")
@login_required
def dashboard():
    user_loans = PenLoans.query.filter_by(borrower_id=current_user.id).all()
    user_donations = PenDonations.query.filter_by(donor_id=current_user.id).all()
    return render_template("dashboard.html", loans=user_loans, donations=user_donations)
@app.route("/loan", methods=["GET", "POST"])
@login_required
def loan():
    if request.method == "POST":
        pen_id = request.form.get("pen_id")
        pen = Pens.query.get(pen_id)
        if not pen:
            return render_template("loan.html", error="Pen not found")

        # Check if pen is available (not loaned)
        active_loan = PenLoans.query.filter_by(pen_id=pen_id, return_date=None).first()
        if active_loan:
            return render_template("loan.html", error="Pen is already loaned")

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
            return render_template("loan.html", error="Loan limit reached for your subscription")
        if pen.class_ not in limits["classes"]:
            return render_template("loan.html", error="Pen class not allowed for your subscription")

        # Create loan
        loan = PenLoans(pen_id=pen_id, lender_id=pen.donations[0].donor_id if pen.donations else 1, borrower_id=user.id)  # Assuming lender is donor
        db.session.add(loan)
        user.pens_loaned += 1
        db.session.commit()
        return redirect(url_for("dashboard"))

    # GET: list available pens
    available_pens = Pens.query.all()
    return render_template("loan.html", pens=available_pens)

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
            sentiment_score = (blob.sentiment.polarity + 1) * 50  # Scale to 0-100
            pen = Pens.query.get(loan.pen_id)
            pen.prs = min(100, pen.prs + sentiment_score)  # Add to PRS, cap at 100
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

@app.route("/sector/sobab/send-email", methods=["POST"])
@login_required
@require_sector("sobab")
def sector_send_email():
    subject = request.form.get("subject", "").strip()
    body = request.form.get("body", "").strip()
    recipient = request.form.get("recipient", "").strip()
    send_all = request.form.get("send_all") == "on"
    if subject and body:
        if send_all:
            for user in Users.query.all():
                if user.email:
                    send_sector_email(user.email, subject, body)
        elif recipient:
            send_sector_email(recipient, subject, body)
    return redirect(url_for("sector_page", sector="sobab"))

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
    if not is_sector_authed("sodac"):
        return redirect(url_for("sector_page", sector="sodac"))

    pen = Pens.query.get(pen_id)
    if not pen:
        return redirect(url_for("sector_page", sector="sodac"))

    if request.method == "POST":
        pen.name = request.form.get("name", pen.name)
        pen.description = request.form.get("description", pen.description)
        pen.ink_level = int(request.form.get("ink_level", pen.ink_level))
        pen.ink_color = request.form.get("ink_color", pen.ink_color)
        pen.class_ = request.form.get("class_", pen.class_)
        pen.prs = int(request.form.get("prs", pen.prs))
        db.session.commit()
        return redirect(url_for("sector_page", sector="sodac"))

    return render_template("edit_pen.html", pen=pen)

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
        picture_filename = None
        if "picture" in request.files:
            file = request.files["picture"]
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to make filename unique
                timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
                filename = timestamp + filename
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                picture_filename = filename

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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
