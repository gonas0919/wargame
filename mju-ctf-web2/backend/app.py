import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from flask import (
    Flask,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import safe_join


BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__, template_folder="templates", static_folder="static")

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "flask-session-secret")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "db")
MYSQL_USER = os.environ.get("MYSQL_USER", "ctf")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "ctfpass")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "jwt_portal")

JWT_SECRET = os.environ.get("JWT_SECRET", "dev_backup_jwt_secret_2026")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "24"))

FLAG_PATH = os.environ.get("FLAG_PATH", "/flag.txt")
BACKUP_DIR = BASE_DIR / "dev_backup"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:3306/{MYSQL_DATABASE}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="user")
    created_at = db.Column(db.DateTime, server_default=db.func.now())


def init_db():
    with app.app_context():
        db.create_all()
        seed_users()


def seed_users():
    guest = User.query.filter_by(username="guest").first()

    if guest is None:
        guest = User(
            username="guest",
            password_hash=generate_password_hash("guest"),
            role="user",
        )
        db.session.add(guest)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def read_flag():
    try:
        with open(FLAG_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "flag file not found"


def create_jwt(user):
    now = datetime.now(timezone.utc)

    payload = {
        "jti": str(uuid.uuid4()),
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRES_HOURS)).timestamp()),
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_token_from_request():
    token = request.cookies.get("token")

    if token:
        return token

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()

    return None


def decode_jwt():
    token = get_token_from_request()

    if not token:
        return None

    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required():
    claims = decode_jwt()
    if claims is None:
        return None
    return claims


def admin_required():
    claims = decode_jwt()

    if claims is None:
        return None

    if claims.get("role") != "admin":
        return None

    return claims


def build_page_response(template_name, **context):
    return render_template(template_name, **context)


@app.get("/style.css")
def style_css():
    return send_from_directory(BASE_DIR / "static", "style.css")


@app.get("/")
def index_page():
    claims = decode_jwt()

    if claims:
        return redirect("/board")

    return build_page_response("index.html")


@app.get("/board")
def dashboard_page():
    claims = login_required()

    if claims is None:
        return redirect("/")

    return build_page_response("board.html", user=claims)


@app.get("/notices")
def notices_page():
    claims = login_required()

    if claims is None:
        return redirect("/")

    return build_page_response("notices.html", user=claims)


@app.get("/resources")
def resources_page():
    claims = login_required()

    if claims is None:
        return redirect("/")

    return build_page_response("resources.html", user=claims)


@app.get("/profile")
def profile_page():
    claims = login_required()

    if claims is None:
        return redirect("/")

    return build_page_response("profile.html", user=claims)


@app.get("/admin")
def admin_page():
    claims = decode_jwt()

    if claims is None:
        return redirect("/")

    if claims.get("role") != "admin":
        return build_page_response(
            "admin.html",
            user=claims,
            is_admin=False,
            flag=None,
            message="Access denied. Administrator privileges required.",
        ), 403

    return build_page_response(
        "admin.html",
        user=claims,
        is_admin=True,
        flag=read_flag(),
        message="Access granted.",
    )


@app.post("/api/login")
def api_login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    user = User.query.filter_by(username=username).first()

    if user is None or not check_password_hash(user.password_hash, password):
        return build_page_response(
            "index.html",
            error="Invalid username or password.",
        ), 401

    token = create_jwt(user)

    response = make_response(redirect("/" \
    "board"))
    response.set_cookie(
        "token",
        token,
        httponly=False,
        samesite="Lax",
        path="/",
    )

    return response


@app.get("/api/logout")
def api_logout():
    response = make_response(redirect("/"))
    response.delete_cookie("token", path="/")
    return response


@app.get("/api/me")
def api_me():
    claims = login_required()

    if claims is None:
        return jsonify({
            "ok": False,
            "message": "login required",
        }), 401

    return jsonify({
        "ok": True,
        "username": claims.get("username"),
        "role": claims.get("role"),
    })


@app.get("/api/admin/flag")
def api_admin_flag():
    claims = admin_required()

    if claims is None:
        return jsonify({
            "ok": False,
            "message": "admin only",
        }), 403

    return jsonify({
        "ok": True,
        "flag": read_flag(),
    })


@app.get("/dev_backup/")
def dev_backup_index():
    if not BACKUP_DIR.exists():
        return "backup directory not found", 404

    files = []

    for item in BACKUP_DIR.iterdir():
        if item.is_file() and item.suffix in [".pcap", ".pcapng", ".cap"]:
            files.append(item.name)

    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Index of /dev_backup/</title>
      <style>
        body { font-family: monospace; padding: 24px; }
        a { display: block; margin: 8px 0; }
      </style>
    </head>
    <body>
      <h1>Index of /dev_backup/</h1>
      <hr>
    """

    for filename in files:
        html += f'<a href="/dev_backup/{filename}">{filename}</a>\n'

    html += """
      <hr>
    </body>
    </html>
    """

    return html


@app.get("/dev_backup/<path:filename>")
def dev_backup_file(filename):
    file_path = safe_join(str(BACKUP_DIR), filename)

    if file_path is None:
        return "invalid path", 400

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        return "file not found", 404

    if path.suffix not in [".pcap", ".pcapng", ".cap"]:
        return "forbidden", 403

    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5020, threaded=True)