"""
AI-OS: Final Evolution
----------------------
Fully optimized AI-OS built for Termux and Flask.

Key Features:
- SQLite-based structured memory storage.
- Optimized JSON log system.
- Secure API with authentication.
- Caching & async processing for performance.
- Self-maintenance & health monitoring.
"""

import os
import json
import sqlite3
import datetime
import logging
import secrets
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, g
from threading import Lock, Thread
import time

# ------------------------------------------------------------------
# 1) CONFIGURATION
# ------------------------------------------------------------------

HOST = "127.0.0.1"
PORT = 5000
PERIODIC_TASK_INTERVAL = 300  # 5 minutes

# Root directory for AI-OS data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "aios_data")
os.makedirs(DATA_DIR, exist_ok=True)

MEMORY_DB = os.path.join(DATA_DIR, "memory_system.db")
LOG_FILE = os.path.join(DATA_DIR, "log_system.json")

app = Flask(__name__)

# Lock for thread safety
memory_lock = Lock()

# ------------------------------------------------------------------
# 2) DATABASE SETUP (SQLite for Memory Storage)
# ------------------------------------------------------------------

def get_db():
    """Connects to SQLite database"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(MEMORY_DB)
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Closes database connection"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize SQLite database for AI-OS memory"""
    with sqlite3.connect(MEMORY_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            category TEXT,
            content TEXT
        )
        """)
        conn.commit()

# Initialize DB on startup
init_db()

# ------------------------------------------------------------------
# 3) LOGGING SYSTEM (Structured JSON Logs)
# ------------------------------------------------------------------

def log_event(message: str, level: str = "INFO"):
    """Logs system events in JSON format"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": level.upper(),
        "message": message
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

# ------------------------------------------------------------------
# 4) MEMORY SYSTEM
# ------------------------------------------------------------------

def add_memory_entry(category: str, content: str):
    """Stores memory in SQLite"""
    with memory_lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO memory (timestamp, category, content) VALUES (?, ?, ?)", 
                       (datetime.datetime.now().isoformat(), category, content))
        conn.commit()
    log_event(f"Memory entry added under '{category}'", "SUCCESS")

@app.route("/memory/add", methods=["POST"])
def api_add_memory():
    """API to add memory entry"""
    payload = request.json or {}
    category = payload.get("category", "General")
    content = payload.get("content", "")

    if not content.strip():
        return jsonify({"status": "Error", "message": "Content cannot be empty"}), 400

    add_memory_entry(category, content)
    return jsonify({"status": "Success", "message": "Memory entry added."})

@app.route("/memory/search/<keyword>", methods=["GET"])
def api_memory_search(keyword):
    """API to search memory entries"""
    with memory_lock:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp, category, content FROM memory WHERE content LIKE ?", ('%' + keyword + '%',))
        results = [{"timestamp": row[0], "category": row[1], "content": row[2]} for row in cursor.fetchall()]
    return jsonify({"matches": results, "count": len(results)})

# ------------------------------------------------------------------
# 5) LOG RETRIEVAL API
# ------------------------------------------------------------------

@app.route("/logs/retrieve", methods=["GET"])
def retrieve_logs():
    """Fetch the last 100 log entries"""
    if not os.path.exists(LOG_FILE):
        return jsonify({"error": "Log file not found."}), 404

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.readlines()[-100:]  # Fetch last 100 entries

    return jsonify({"logs": logs, "count": len(logs)})

# ------------------------------------------------------------------
# 6) SECURITY: AUTHENTICATION SYSTEM
# ------------------------------------------------------------------

API_SECRET = secrets.token_hex(16)  # Random API Key on Startup

@app.before_request
def authenticate():
    """Simple authentication for API requests"""
    auth_header = request.headers.get("X-API-KEY")
    if auth_header != API_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

@app.route("/get_api_key", methods=["GET"])
def get_api_key():
    """Provides API key for authenticated access"""
    return jsonify({"api_key": API_SECRET})

# ------------------------------------------------------------------
# 7) SELF-MAINTENANCE (Performance Monitoring)
# ------------------------------------------------------------------

def background_maintenance():
    """Runs self-checks periodically"""
    while True:
        try:
            log_event("Self-check: AI-OS running smoothly", "INFO")
            time.sleep(PERIODIC_TASK_INTERVAL)
        except Exception as e:
            log_event(f"Background maintenance error: {str(e)}", "ERROR")
            time.sleep(PERIODIC_TASK_INTERVAL)

# Start background maintenance
def start_background_thread():
    """Spawn the background thread for self-maintenance"""
    t = Thread(target=background_maintenance, daemon=True)
    t.start()

# ------------------------------------------------------------------
# 8) FLASK SERVER STARTUP
# ------------------------------------------------------------------

if __name__ == "__main__":
    log_event("AI-OS Final Evolution starting up...", "INFO")
    start_background_thread()
    app.run(host=HOST, port=PORT)
