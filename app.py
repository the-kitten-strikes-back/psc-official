

from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import datetime
import os
from textblob import TextBlob
app = Flask(__name__)
db_uri = "postgresql+psycopg2://database_k306_user:tlPqDUbqa9LffCdK5QcqkqTjQDEOqAtT@dpg-d6onjpq4d50c73blir8g-a/database_k306"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", db_uri)
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 280,
    'pool_pre_ping': True,
}

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "1024supersecretkey!1024")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "static/pens")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

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
class PenDonations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pen_id = db.Column(db.Integer, db.ForeignKey("pens.id"), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    donation_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(50), default="Pending") #Pending, Accepted, Rejected. Pending means the pen is waiting to be approved by an admin, accepted means the pen is approved and added to the inventory, rejected means the pen is rejected and won't be added to the inventory.
    donor = db.relationship('Users', backref='donations')
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

        ADMIN_PASSWORD = "psc_founder_2025"

        if password == ADMIN_PASSWORD:
            current_user.is_admin = True
            db.session.commit()

            print(f"User {current_user.username} is now an admin!")

        else:
            print(f"Failed admin attempt by {current_user.username}")

    return render_template("about.html")

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
    if not current_user.is_admin:
        return redirect(url_for("dashboard"))

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

@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for("home"))

    all_pens = Pens.query.all()
    pending_donations = PenDonations.query.filter_by(status="Pending").all()
    accepted_donations = PenDonations.query.filter_by(status="Accepted").all()
    rejected_donations = PenDonations.query.filter_by(status="Rejected").all()
    all_users = Users.query.all()

    return render_template("admin.html",
                         pens=all_pens,
                         pending_donations=pending_donations,
                         accepted_donations=accepted_donations,
                         rejected_donations=rejected_donations,
                         users=all_users)

@app.route("/admin/donation/<int:donation_id>/approve", methods=["POST"])
@login_required
def approve_donation(donation_id):
    if not current_user.is_admin:
        return redirect(url_for("home"))

    donation = PenDonations.query.get(donation_id)
    if donation:
        donation.status = "Accepted"
        db.session.commit()

    return redirect(url_for("admin"))

@app.route("/admin/donation/<int:donation_id>/reject", methods=["POST"])
@login_required
def reject_donation(donation_id):
    if not current_user.is_admin:
        return redirect(url_for("home"))

    donation = PenDonations.query.get(donation_id)
    if donation:
        donation.status = "Rejected"
        db.session.commit()

    return redirect(url_for("admin"))

@app.route("/admin/pen/<int:pen_id>/edit", methods=["GET", "POST"])
@login_required
def edit_pen(pen_id):
    if not current_user.is_admin:
        return redirect(url_for("home"))

    pen = Pens.query.get(pen_id)
    if not pen:
        return redirect(url_for("admin"))

    if request.method == "POST":
        pen.name = request.form.get("name", pen.name)
        pen.description = request.form.get("description", pen.description)
        pen.ink_level = int(request.form.get("ink_level", pen.ink_level))
        pen.ink_color = request.form.get("ink_color", pen.ink_color)
        pen.class_ = request.form.get("class_", pen.class_)
        pen.prs = int(request.form.get("prs", pen.prs))
        db.session.commit()
        return redirect(url_for("admin"))

    return render_template("edit_pen.html", pen=pen)

@app.route("/admin/pen/<int:pen_id>/delete", methods=["POST"])
@login_required
def delete_pen(pen_id):
    if not current_user.is_admin:
        return redirect(url_for("home"))

    pen = Pens.query.get(pen_id)
    if pen:
        db.session.delete(pen)
        db.session.commit()

    return redirect(url_for("admin"))

@app.route("/admin/user/<int:user_id>/toggle-admin", methods=["POST"])
@login_required
def toggle_admin(user_id):
    if not current_user.is_admin:
        return redirect(url_for("home"))

    user = Users.query.get(user_id)
    if user and user.id != current_user.id:  # Prevent self-demotion
        user.is_admin = not user.is_admin
        db.session.commit()

    return redirect(url_for("admin"))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/admin/add-pen", methods=["GET", "POST"])
@login_required
def add_pen():
    if not current_user.is_admin:
        return redirect(url_for("home"))

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
        return redirect(url_for("admin"))

    return render_template("add_pen.html")
@app.route("/partnerships")
def partnerships():
    return render_template("partnerships.html")
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
