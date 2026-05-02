from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import logging
import os
import psycopg2
from datetime import datetime

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
app.secret_key = "temporary-secret-key"

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
    return redirect(url_for("login"))


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/login")
def login():
    session["user"] = "demo-user"
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/containers")
def containers():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("containers.html")


@app.route("/alerts")
def alerts():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("alerts.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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