from datetime import datetime
from pathlib import Path
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "queue.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-development-secret"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_number INTEGER NOT NULL,
                token_label TEXT NOT NULL,
                patient_name TEXT NOT NULL,
                department TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Waiting'
                    CHECK(status IN ('Waiting', 'Serving', 'Completed', 'Cancelled')),
                created_at TEXT NOT NULL,
                called_at TEXT,
                completed_at TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_patients_status_token
            ON patients(status, token_number)
        """)


def next_token_number(conn):
    # Tokens restart each day, while the database keeps previous records.
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COALESCE(MAX(token_number), 0) + 1 AS next_no "
        "FROM patients WHERE substr(created_at, 1, 10) = ?",
        (today,)
    ).fetchone()
    return row["next_no"]


def current_queue(conn):
    return conn.execute("""
        SELECT id, token_number, token_label, patient_name, department, status,
               created_at, called_at, completed_at
        FROM patients
        WHERE status IN ('Waiting', 'Serving')
        ORDER BY CASE status WHEN 'Serving' THEN 0 ELSE 1 END, token_number
    """).fetchall()


def estimated_wait_minutes(conn, patient):
    if patient["status"] == "Serving":
        return 0
    if patient["status"] != "Waiting":
        return 0

    serving = conn.execute(
        "SELECT COUNT(*) AS n FROM patients WHERE status = 'Serving'"
    ).fetchone()["n"]
    ahead = conn.execute("""
        SELECT COUNT(*) AS n FROM patients
        WHERE status = 'Waiting'
          AND token_number < ?
          AND substr(created_at, 1, 10) = ?
    """, (patient["token_number"], datetime.now().strftime("%Y-%m-%d"))).fetchone()["n"]

    # Demo assumption: average service time is 5 minutes per patient.
    return (serving + ahead) * 5


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("patient_name", "").strip()
    department = request.form.get("department", "").strip()
    allowed_departments = {"General Medicine", "Pediatrics", "Orthopedics", "Dermatology", "Cardiology"}

    if not name or len(name) > 80:
        flash("Please enter a patient name (up to 80 characters).", "error")
        return redirect(url_for("home"))
    if department not in allowed_departments:
        flash("Please select a valid department.", "error")
        return redirect(url_for("home"))

    now = datetime.now().isoformat(timespec="seconds")
    with get_db() as conn:
        number = next_token_number(conn)
        label = f"A{number:03d}"
        conn.execute("""
            INSERT INTO patients
                (token_number, token_label, patient_name, department, status, created_at)
            VALUES (?, ?, ?, ?, 'Waiting', ?)
        """, (number, label, name, department, now))
        patient_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    return redirect(url_for("token_page", patient_id=patient_id))


@app.route("/token/<int:patient_id>")
def token_page(patient_id):
    with get_db() as conn:
        patient = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if patient is None:
            abort(404)
        wait = estimated_wait_minutes(conn, patient)
    return render_template("token.html", patient=patient, wait=wait)


@app.route("/staff")
def staff():
    with get_db() as conn:
        queue = current_queue(conn)
        totals = {
            "waiting": conn.execute("SELECT COUNT(*) FROM patients WHERE status='Waiting'").fetchone()[0],
            "serving": conn.execute("SELECT COUNT(*) FROM patients WHERE status='Serving'").fetchone()[0],
            "completed": conn.execute(
                "SELECT COUNT(*) FROM patients WHERE status='Completed' AND substr(created_at,1,10)=?",
                (datetime.now().strftime("%Y-%m-%d"),)
            ).fetchone()[0],
        }
        recent = conn.execute("""
            SELECT * FROM patients
            WHERE substr(created_at,1,10)=?
            ORDER BY token_number DESC LIMIT 10
        """, (datetime.now().strftime("%Y-%m-%d"),)).fetchall()
    return render_template("staff.html", queue=queue, totals=totals, recent=recent)


@app.route("/staff/call-next", methods=["POST"])
def call_next():
    with get_db() as conn:
        active = conn.execute("SELECT id FROM patients WHERE status='Serving' LIMIT 1").fetchone()
        if active:
            flash("Complete the currently serving patient before calling the next.", "error")
        else:
            patient = conn.execute("""
                SELECT id FROM patients WHERE status='Waiting'
                ORDER BY token_number ASC LIMIT 1
            """).fetchone()
            if patient:
                conn.execute(
                    "UPDATE patients SET status='Serving', called_at=? WHERE id=?",
                    (datetime.now().isoformat(timespec="seconds"), patient["id"])
                )
                flash("Next patient has been called.", "success")
            else:
                flash("There are no patients waiting.", "error")
    return redirect(url_for("staff"))


@app.route("/staff/complete/<int:patient_id>", methods=["POST"])
def complete_patient(patient_id):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM patients WHERE id=?", (patient_id,)).fetchone()
        if row is None:
            abort(404)
        if row["status"] != "Serving":
            flash("Only the currently serving patient can be completed.", "error")
        else:
            conn.execute(
                "UPDATE patients SET status='Completed', completed_at=? WHERE id=?",
                (datetime.now().isoformat(timespec="seconds"), patient_id)
            )
            flash("Patient marked as completed.", "success")
    return redirect(url_for("staff"))


@app.route("/staff/cancel/<int:patient_id>", methods=["POST"])
def cancel_patient(patient_id):
    with get_db() as conn:
        row = conn.execute("SELECT status FROM patients WHERE id=?", (patient_id,)).fetchone()
        if row is None:
            abort(404)
        if row["status"] != "Waiting":
            flash("Only waiting patients can be cancelled.", "error")
        else:
            conn.execute("UPDATE patients SET status='Cancelled' WHERE id=?", (patient_id,))
            flash("Waiting token cancelled.", "success")
    return redirect(url_for("staff"))


@app.route("/display")
def display():
    return render_template("display.html")


@app.route("/api/queue")
def api_queue():
    with get_db() as conn:
        active = conn.execute("""
            SELECT token_label, department FROM patients
            WHERE status='Serving' ORDER BY called_at DESC LIMIT 1
        """).fetchone()
        waiting = conn.execute("""
            SELECT token_label, department, created_at FROM patients
            WHERE status='Waiting' AND substr(created_at,1,10)=?
            ORDER BY token_number ASC
        """, (datetime.now().strftime("%Y-%m-%d"),)).fetchall()
        counts = conn.execute("""
            SELECT
                SUM(CASE WHEN status='Waiting' THEN 1 ELSE 0 END) AS waiting,
                SUM(CASE WHEN status='Serving' THEN 1 ELSE 0 END) AS serving
            FROM patients WHERE substr(created_at,1,10)=?
        """, (datetime.now().strftime("%Y-%m-%d"),)).fetchone()

    return jsonify({
        "current": dict(active) if active else None,
        "waiting": [dict(row) for row in waiting],
        "waiting_count": counts["waiting"] or 0,
        "serving_count": counts["serving"] or 0,
        "updated_at": datetime.now().strftime("%H:%M:%S")
    })


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


init_db()

if __name__ == "__main__":
    app.run(debug=True)
