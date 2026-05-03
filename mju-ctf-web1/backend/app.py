import os
import time
import uuid

from flask import Flask, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError


app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

INITIAL_MILEAGE = 1000
FLAG_PATH = os.environ.get("FLAG_PATH", "/flag.txt")

MYSQL_HOST = os.environ.get("MYSQL_HOST", "db")
MYSQL_USER = os.environ.get("MYSQL_USER", "ctf")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "ctfpass")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "course_rush")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:3306/{MYSQL_DATABASE}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


COURSES = [
    {
        "id": "web-hacking-starter",
        "title": "Web Hacking Starter",
        "category": "Web Hacking",
        "level": "Starter",
        "mileage": 1000,
    },
    {
        "id": "web-hacking-advanced",
        "title": "Web Hacking Advanced",
        "category": "Web Hacking",
        "level": "Advanced",
        "mileage": 1000,
    },
    {
        "id": "pwnable-starter",
        "title": "Pwnable Starter",
        "category": "Pwnable",
        "level": "Starter",
        "mileage": 1000,
    },
    {
        "id": "pwnable-advanced",
        "title": "Pwnable Advanced",
        "category": "Pwnable",
        "level": "Advanced",
        "mileage": 1000,
    },
    {
        "id": "reversing-starter",
        "title": "Reversing Starter",
        "category": "Reversing",
        "level": "Starter",
        "mileage": 1000,
    },
    {
        "id": "reversing-advanced",
        "title": "Reversing Advanced",
        "category": "Reversing",
        "level": "Advanced",
        "mileage": 1000,
    },
    {
        "id": "digital-forensics-starter",
        "title": "Digital Forensics Starter",
        "category": "Digital Forensics",
        "level": "Starter",
        "mileage": 1000,
    },
    {
        "id": "digital-forensics-advanced",
        "title": "Digital Forensics Advanced",
        "category": "Digital Forensics",
        "level": "Advanced",
        "mileage": 1000,
    },
]

COURSES_BY_ID = {course["id"]: course for course in COURSES}


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(64), unique=True, nullable=False)
    mileage = db.Column(db.Integer, nullable=False, default=INITIAL_MILEAGE)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


def init_db():
    with app.app_context():
        db.create_all()


def read_flag():
    try:
        with open(FLAG_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "flag file not found"


def get_sid():
    if "sid" not in session:
        session["sid"] = str(uuid.uuid4())
    return session["sid"]


def get_current_user():
    sid = get_sid()

    user = User.query.filter_by(sid=sid).first()
    if user is not None:
        return user

    user = User(sid=sid, mileage=INITIAL_MILEAGE)
    db.session.add(user)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        user = User.query.filter_by(sid=sid).first()

    return user


def get_paid_amount(user_id, course_id):
    result = (
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter_by(user_id=user_id, course_id=course_id)
        .scalar()
    )
    return int(result)


def is_enrolled(user_id, course_id):
    return (
        Enrollment.query
        .filter_by(user_id=user_id, course_id=course_id)
        .first()
        is not None
    )


def course_status(user, course):
    paid = get_paid_amount(user.id, course["id"])
    enrolled = is_enrolled(user.id, course["id"])

    return {
        **course,
        "paid": paid,
        "enrolled": enrolled,
        "available": user.mileage >= course["mileage"],
    }


def public_state(user):
    enrolled_courses = [
        course_status(user, course)
        for course in COURSES
        if is_enrolled(user.id, course["id"])
    ]

    data = {
        "sid": session.get("sid"),
        "mileage": user.mileage,
        "courses": [course_status(user, course) for course in COURSES],
        "enrolled_courses": enrolled_courses,
        "enrolled_count": len(enrolled_courses),
    }

    return data


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/status")
def status():
    user = get_current_user()
    return jsonify(public_state(user))


@app.get("/api/courses")
def courses():
    user = get_current_user()
    return jsonify(public_state(user))


@app.get("/api/courses/<course_id>")
def course_detail(course_id):
    user = get_current_user()

    course = COURSES_BY_ID.get(course_id)
    if course is None:
        return jsonify({"message": "course not found"}), 404

    data = {
        "mileage": user.mileage,
        "course": course_status(user, course),
    }

    return jsonify(data)


@app.get("/api/me/courses")
def my_courses():
    user = get_current_user()

    enrolled_courses = [
        course_status(user, course)
        for course in COURSES
        if is_enrolled(user.id, course["id"])
    ]

    data = {
        "mileage": user.mileage,
        "courses": enrolled_courses,
        "enrolled_count": len(enrolled_courses),
    }

    if len(enrolled_courses) >= 2:
        data["flag"] = read_flag()

    return jsonify(data)


@app.post("/api/enroll")
def enroll():
    user = get_current_user()

    payload = request.get_json(silent=True) or {}
    course_id = payload.get("course_id")
    course = COURSES_BY_ID.get(course_id)

    if course is None:
        return jsonify({"ok": False, "message": "course not found"}), 404

    if is_enrolled(user.id, course_id):
        return jsonify({
            "ok": True,
            "message": "already enrolled",
            **public_state(user),
        })  

    enrolled_count = Enrollment.query.filter_by(user_id=user.id).count()

    if enrolled_count >= 1:
        return jsonify({
            "ok": False,
            "message": "You can enroll only one course.",
            **public_state(user),
        }), 400

    time.sleep(1)

    enrollment = Enrollment(
        user_id=user.id,
        course_id=course_id,
    )

    payment = Payment(
        user_id=user.id,
        course_id=course_id,
        amount=course["mileage"],
    )

    db.session.add(enrollment)
    db.session.add(payment)

    db.session.execute(
        text("""
            UPDATE users
            SET mileage = mileage - :amount
            WHERE id = :user_id
        """),
        {
            "amount": course["mileage"],
            "user_id": user.id,
        }
    )

    try:
        db.session.commit()
    except OperationalError as e:
        db.session.rollback()

        error_code = None
        if hasattr(e.orig, "args") and len(e.orig.args) > 0:
            error_code = e.orig.args[0]

        if error_code in (1205, 1213):
            return jsonify({
                "ok": False,
                "message": "server is busy, please try again",
            }), 409

        return jsonify({
            "ok": False,
            "message": "database error",
        }), 500

    db.session.refresh(user)

    return jsonify({
        "ok": True,
        "message": "enrollment request has been processed",
        **public_state(user),
    })


@app.post("/api/reset")
def reset():
    user = get_current_user()

    Payment.query.filter_by(user_id=user.id).delete()
    Enrollment.query.filter_by(user_id=user.id).delete()

    user.mileage = INITIAL_MILEAGE

    db.session.commit()

    return jsonify(public_state(user))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5010, threaded=True)
