from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import MYSQL_CONFIG, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY


# -------------------------
# CONEXIÓN DB
# -------------------------
def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


# -------------------------
# CREAR TABLAS AUTOMÁTICAMENTE
# -------------------------
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(100) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        is_admin BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        competition VARCHAR(120) NOT NULL,
        match_date DATETIME NOT NULL,
        home_team VARCHAR(120) NOT NULL,
        away_team VARCHAR(120) NOT NULL,
        predicted_result VARCHAR(50) NOT NULL,
        predicted_home_score INT DEFAULT NULL,
        predicted_away_score INT DEFAULT NULL,
        confidence_level VARCHAR(30) DEFAULT 'Media',
        analysis TEXT,
        status VARCHAR(30) DEFAULT 'Pendiente',
        actual_home_score INT DEFAULT NULL,
        actual_away_score INT DEFAULT NULL,
        created_by INT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cursor.close()
    conn.close()


# -------------------------
# CREAR ADMIN AUTOMÁTICO
# -------------------------
def create_admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE username = %s", ("admin",))
    user = cursor.fetchone()

    if not user:
        password_hash = generate_password_hash("123admin123")
        cursor.execute("""
            INSERT INTO users (username, password_hash, is_admin)
            VALUES (%s, %s, %s)
        """, ("admin", password_hash, True))
        conn.commit()

    cursor.close()
    conn.close()


# Ejecutar al iniciar
with app.app_context():
    create_tables()
    create_admin()


# -------------------------
# DECORADORES
# -------------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


# -------------------------
# RUTAS
# -------------------------
@app.route("/")
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM predictions ORDER BY match_date ASC")
    predictions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("index.html", predictions=predictions)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["is_admin"] = user["is_admin"]
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Credenciales incorrectas")

        cursor.close()
        conn.close()

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM predictions ORDER BY created_at DESC")
    predictions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin.html", predictions=predictions)


@app.route("/admin/add_prediction", methods=["POST"])
@admin_required
def add_prediction():
    data = request.form

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO predictions (
            competition, match_date, home_team, away_team,
            predicted_result, predicted_home_score, predicted_away_score,
            confidence_level, analysis, created_by
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data["competition"],
        data["match_date"],
        data["home_team"],
        data["away_team"],
        data["predicted_result"],
        data.get("predicted_home_score") or None,
        data.get("predicted_away_score") or None,
        data["confidence_level"],
        data["analysis"],
        session["user_id"]
    ))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete/<int:id>", methods=["POST"])
@admin_required
def delete_prediction(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM predictions WHERE id = %s", (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/update_result/<int:id>", methods=["POST"])
@admin_required
def update_result(id):
    home = request.form.get("actual_home_score")
    away = request.form.get("actual_away_score")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE predictions
        SET actual_home_score=%s, actual_away_score=%s
        WHERE id=%s
    """, (home, away, id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for("admin_dashboard"))


# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)