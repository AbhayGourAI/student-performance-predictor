import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from flask import Flask, jsonify, request
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.environ.get("MODEL_PATH", BASE_DIR / "model.joblib"))
DB_PATH = os.environ.get("DB_PATH", str(BASE_DIR / "predictions.db"))
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": FRONTEND_ORIGIN}})

FEATURES = ["study_hours", "attendance", "previous_score", "sleep_hours"]
LIMITS = {
    "study_hours": (0, 16),
    "attendance": (0, 100),
    "previous_score": (0, 100),
    "sleep_hours": (0, 24),
}

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                study_hours REAL NOT NULL,
                attendance REAL NOT NULL,
                previous_score REAL NOT NULL,
                sleep_hours REAL NOT NULL,
                predicted_score REAL NOT NULL
            )
        """)

def get_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model file not found at {MODEL_PATH}. Run python train_model.py first."
        )
    bundle = joblib.load(MODEL_PATH)
    return bundle["model"]

def validate_payload(payload):
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."

    values = {}
    for key, (minimum, maximum) in LIMITS.items():
        if key not in payload:
            return None, f"Missing required field: {key}"
        try:
            value = float(payload[key])
        except (TypeError, ValueError):
            return None, f"{key} must be a number."
        if not np.isfinite(value):
            return None, f"{key} must be a finite number."
        if not minimum <= value <= maximum:
            return None, f"{key} must be between {minimum} and {maximum}."
        values[key] = value
    return values, None

@app.get("/")
def home():
    return jsonify({
        "message": "Student Performance Predictor API",
        "endpoints": ["/api/health", "/api/predict", "/api/history"]
    })

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model_loaded": MODEL_PATH.exists()})

@app.post("/api/predict")
def predict():
    values, error = validate_payload(request.get_json(silent=True))
    if error:
        return jsonify({"error": error}), 400

    try:
        model = get_model()
        row = [[values[name] for name in FEATURES]]
        score = float(np.clip(model.predict(row)[0], 0, 100))
        score = round(score, 1)

        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """INSERT INTO predictions
                (created_at, study_hours, attendance, previous_score, sleep_hours, predicted_score)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    values["study_hours"], values["attendance"],
                    values["previous_score"], values["sleep_hours"], score
                )
            )

        if score >= 80:
            label = "Strong predicted performance"
        elif score >= 60:
            label = "Moderate predicted performance"
        else:
            label = "There may be room to improve"

        return jsonify({
            "predicted_score": score,
            "interpretation": label,
            "notice": "Demo estimate from a model trained on synthetic data; not an actual academic assessment."
        })
    except FileNotFoundError as exc:
        app.logger.exception("Model file missing")
        return jsonify({"error": str(exc)}), 500
    except Exception:
        app.logger.exception("Prediction failed")
        return jsonify({"error": "Prediction failed. Check the backend logs."}), 500

@app.get("/api/history")
def history():
    try:
        init_db()
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """SELECT id, created_at, study_hours, attendance,
                previous_score, sleep_hours, predicted_score
                FROM predictions ORDER BY id DESC LIMIT 20"""
            ).fetchall()
        return jsonify({"history": [dict(row) for row in rows]})
    except Exception:
        app.logger.exception("Could not read prediction history")
        return jsonify({"error": "Could not load prediction history."}), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
