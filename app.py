from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import logging
import msal
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
from functools import wraps


app = Flask(__name__)
load_dotenv()

app.config["JSON_SORT_KEYS"] = False
app.secret_key = os.getenv("FLASK_SECRET_KEY", "temporary-secret-key")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
TENANT_ID = os.getenv("TENANT_ID")
REDIRECT_PATH = os.getenv("REDIRECT_PATH", "/getAToken")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["User.Read"]

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename="logs/app.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

DB_HOST = os.getenv("DB_HOST", "pg-monitoring-es.postgres.database.azure.com")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER", "pgadminbisera")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

USE_DATABASE = False


def get_redirect_uri():
    """
    Local Flask uses http://localhost:5000/getAToken.
    Azure Container Apps must use https://.../getAToken.
    """
    app_base_url = os.getenv("APP_BASE_URL")

    if app_base_url:
        return app_base_url.rstrip("/") + REDIRECT_PATH

    return url_for("authorized", _external=True)


def build_msal_app():
    return msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET
    )


def login_required(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return route(*args, **kwargs)
    return wrapper


def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT,
        sslmode="require"
    )


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_metrics (
            id SERIAL PRIMARY KEY,
            device_name VARCHAR(100) NOT NULL,
            cpu_percent FLOAT NOT NULL,
            memory_percent FLOAT NOT NULL,
            disk_percent FLOAT NOT NULL,
            timestamp TIMESTAMP NOT NULL
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
def home():
    return redirect(url_for("dashboard"))


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/login")
def login():
    redirect_uri = get_redirect_uri()

    auth_url = build_msal_app().get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=redirect_uri
    )

    return redirect(auth_url)


@app.route(REDIRECT_PATH)
def authorized():
    if not request.args.get("code"):
        return "Login failed: no authorization code received"

    redirect_uri = get_redirect_uri()

    result = build_msal_app().acquire_token_by_authorization_code(
        request.args["code"],
        scopes=SCOPE,
        redirect_uri=redirect_uri
    )

    if "id_token_claims" in result:
        session["user"] = result["id_token_claims"]
        return redirect(url_for("dashboard"))

    return "Login failed: " + str(result.get("error_description"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/containers")
@login_required
def containers():
    return render_template("containers.html")


@app.route("/alerts")
@login_required
def alerts():
    return render_template("alerts.html")


@app.route("/logout")
def logout():
    session.clear()

    post_logout_url = os.getenv("APP_BASE_URL")
    if post_logout_url:
        post_logout_url = post_logout_url.rstrip() + "/login"
    else:
        post_logout_url = url_for("login", _external=True)

    return redirect(
        f"{AUTHORITY}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={post_logout_url}"
    )


@app.route("/api/metrics", methods=["POST"])
def receive_metrics():
    if not USE_DATABASE:
        return jsonify({
            "message": "Mock mode is enabled. Database storage is disabled.",
            "received_data": request.get_json()
        }), 200

    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        required_fields = [
            "device_name",
            "cpu_percent",
            "memory_percent",
            "disk_percent",
            "timestamp"
        ]

        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing field: {field}"}), 400

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO monitoring_metrics
            (device_name, cpu_percent, memory_percent, disk_percent, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data["device_name"],
            data["cpu_percent"],
            data["memory_percent"],
            data["disk_percent"],
            data["timestamp"]
        ))

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": "Metrics received and stored successfully",
            "data": data
        }), 201

    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    if not USE_DATABASE:
        return jsonify({
            "system_status": "Online",
            "device_name": "server-01",
            "cpu_percent": 35,
            "memory_percent": 62,
            "disk_percent": 70,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 200

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT id, device_name, cpu_percent, memory_percent, disk_percent, timestamp
            FROM monitoring_metrics
            ORDER BY id DESC
            LIMIT 10
        """)

        rows = cur.fetchall()

        cur.close()
        conn.close()

        result = []

        for row in rows:
            result.append({
                "id": row[0],
                "device_name": row[1],
                "cpu_percent": row[2],
                "memory_percent": row[3],
                "disk_percent": row[4],
                "timestamp": str(row[5])
            })

        return jsonify(result), 200

    except Exception as e:
        logging.error(f"Error reading metrics: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/containers")
def api_containers():
    return jsonify([
        {
            "name": "frontend",
            "status": "Running",
            "cpu_percent": 12,
            "memory_usage": "180 MB",
            "uptime": "2 days, 4 hours"
        },
        {
            "name": "backend-api",
            "status": "Running",
            "cpu_percent": 18,
            "memory_usage": "250 MB",
            "uptime": "2 days, 4 hours"
        },
        {
            "name": "data-collector",
            "status": "Running",
            "cpu_percent": 9,
            "memory_usage": "120 MB",
            "uptime": "2 days, 4 hours"
        }
    ]), 200


@app.route("/api/alerts")
def api_alerts():
    return jsonify([
        {
            "severity": "High",
            "message": "Disk usage is above 85%",
            "source": "server-01",
            "status": "Open"
        },
        {
            "severity": "Medium",
            "message": "CPU usage is above 80%",
            "source": "server-01",
            "status": "Open"
        },
        {
            "severity": "Low",
            "message": "Container collector restarted",
            "source": "data-collector",
            "status": "Resolved"
        }
    ]), 200


if __name__ == "__main__":
    if USE_DATABASE:
        create_table()

    app.run(host="0.0.0.0", port=5000, debug=True)