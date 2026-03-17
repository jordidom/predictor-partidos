from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from config import MYSQL_CONFIG, SECRET_KEY

app = Flask(__name__)
app.secret_key = SECRET_KEY


def get_db_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para acceder.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or not session.get("is_admin"):
            flash("No tienes permisos para acceder.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def index():
    conn = None
    cursor = None
    predictions = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM predictions
            ORDER BY match_date ASC, created_at DESC
        """)
        predictions = cursor.fetchall()
    except Error as e:
        flash(f"Error al cargar predicciones: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("index.html", predictions=predictions)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = None
        cursor = None

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()

            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["is_admin"] = bool(user["is_admin"])
                flash("Sesión iniciada correctamente.", "success")
                return redirect(url_for("admin_dashboard"))
            else:
                flash("Usuario o contraseña incorrectos.", "danger")
        except Error as e:
            flash(f"Error al iniciar sesión: {e}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = None
    cursor = None
    predictions = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT *
            FROM predictions
            ORDER BY created_at DESC
        """)
        predictions = cursor.fetchall()
    except Error as e:
        flash(f"Error al cargar el panel: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return render_template("admin.html", predictions=predictions)


@app.route("/admin/add_prediction", methods=["POST"])
@admin_required
def add_prediction():
    competition = request.form.get("competition", "").strip()
    match_date = request.form.get("match_date", "").strip()
    home_team = request.form.get("home_team", "").strip()
    away_team = request.form.get("away_team", "").strip()
    predicted_result = request.form.get("predicted_result", "").strip()
    predicted_home_score = request.form.get("predicted_home_score")
    predicted_away_score = request.form.get("predicted_away_score")
    confidence_level = request.form.get("confidence_level", "Media").strip()
    analysis = request.form.get("analysis", "").strip()

    if not all([competition, match_date, home_team, away_team, predicted_result]):
        flash("Completa todos los campos obligatorios.", "warning")
        return redirect(url_for("admin_dashboard"))

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions (
                competition,
                match_date,
                home_team,
                away_team,
                predicted_result,
                predicted_home_score,
                predicted_away_score,
                confidence_level,
                analysis,
                created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            competition,
            match_date,
            home_team,
            away_team,
            predicted_result,
            predicted_home_score if predicted_home_score else None,
            predicted_away_score if predicted_away_score else None,
            confidence_level,
            analysis,
            session["user_id"]
        ))
        conn.commit()
        flash("Predicción creada correctamente.", "success")
    except Error as e:
        flash(f"Error al guardar la predicción: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/delete_prediction/<int:prediction_id>", methods=["POST"])
@admin_required
def delete_prediction(prediction_id):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM predictions WHERE id = %s", (prediction_id,))
        conn.commit()
        flash("Predicción eliminada.", "info")
    except Error as e:
        flash(f"Error al eliminar: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/update_result/<int:prediction_id>", methods=["POST"])
@admin_required
def update_result(prediction_id):
    actual_home_score = request.form.get("actual_home_score")
    actual_away_score = request.form.get("actual_away_score")

    if actual_home_score == "" or actual_away_score == "":
        flash("Debes poner ambos resultados reales.", "warning")
        return redirect(url_for("admin_dashboard"))

    if int(actual_home_score) > int(actual_away_score):
        status = "Acertada" if request.form.get("predicted_result") == "1" else "Fallada"
    elif int(actual_home_score) < int(actual_away_score):
        status = "Acertada" if request.form.get("predicted_result") == "2" else "Fallada"
    else:
        status = "Acertada" if request.form.get("predicted_result") == "X" else "Fallada"

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE predictions
            SET actual_home_score = %s,
                actual_away_score = %s,
                status = %s
            WHERE id = %s
        """, (actual_home_score, actual_away_score, status, prediction_id))
        conn.commit()
        flash("Resultado actualizado.", "success")
    except Error as e:
        flash(f"Error al actualizar resultado: {e}", "danger")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return redirect(url_for("admin_dashboard"))


@app.route("/api/predictions")
def api_predictions():
    conn = None
    cursor = None
    predictions = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, competition, match_date, home_team, away_team,
                   predicted_result, predicted_home_score, predicted_away_score,
                   confidence_level, analysis, status
            FROM predictions
            ORDER BY match_date ASC
        """)
        predictions = cursor.fetchall()
    except Error:
        predictions = []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    return jsonify(predictions)


if __name__ == "__main__":
    app.run(debug=True)