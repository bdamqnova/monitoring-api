import os
import socket
import datetime
import requests
import psutil

API_URL = os.getenv("MONITORING_API_URL")
API_KEY = os.getenv("MONITORING_API_KEY")


def collect_metrics():
    """Collect basic system metrics from the client device."""
    return {
        "device_name": socket.gethostname(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage("/").percent,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
    }


def send_metrics():
    """Send collected metrics to the monitoring API."""
    if not API_URL:
        print("Error: MONITORING_API_URL is not set")
        return

    data = collect_metrics()

    headers = {
        "Content-Type": "application/json"
    }

    if API_KEY:
        headers["X-API-Key"] = API_KEY

    try:
        response = requests.post(
            API_URL,
            json=data,
            headers=headers,
            timeout=30
        )

        print("Status:", response.status_code)
        print(response.text)

    except requests.exceptions.RequestException as e:
        print("Connection error:", e)


if __name__ == "__main__":
    send_metrics()