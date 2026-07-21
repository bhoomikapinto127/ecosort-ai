"""
app.py
Flask backend for the EcoSort AI dashboard.

Routes:
    GET  /                        -> dashboard page
    GET  /api/bins                -> list all smart bins
    GET  /api/bins/<id>           -> single bin detail
    GET  /api/bins/<id>/history   -> recent waste log entries for a bin
    POST /api/bins/<id>/collect   -> empty a bin
    POST /api/upload              -> upload waste image -> AI classify -> update bin
    POST /api/simulate            -> manually trigger one IoT sensor tick (demo)
    GET  /api/summary             -> Weekly Summary cards (kg + % change per category)
    GET  /api/distribution        -> Waste Distribution pie chart data
    GET  /api/trend               -> Weekly Trend line chart data (Mon..Sun)
    GET  /api/notifications       -> bell icon badge count + alert list

Run:
    pip install flask groq
    export GROQ_API_KEY="your-key-here"
    python app.py
"""

import os
import threading
import time
from flask import Flask, request, jsonify, render_template

import database
import ai_helper

app = Flask(__name__)
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
database.init_db()


def iot_simulator_loop(interval_seconds=15):
    """
    Background thread that fakes real IoT sensor pushes: every
    `interval_seconds`, nudge each bin's fill level and temperature.
    In a real deployment this loop would instead be replaced by
    incoming MQTT/HTTP messages from physical sensors.
    """
    while True:
        time.sleep(interval_seconds)
        database.simulate_sensor_tick()


# Start the simulator once, in a daemon thread, when the app boots.
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    threading.Thread(target=iot_simulator_loop, daemon=True).start()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scanner")
def scanner_page():
    return render_template("scanner.html")


# ---------------------------------------------------------------------
# Smart Bins
# ---------------------------------------------------------------------

@app.route("/api/bins", methods=["GET"])
def api_get_bins():
    return jsonify(database.get_all_bins())


@app.route("/api/bins/<int:bin_id>", methods=["GET"])
def api_get_bin(bin_id):
    bin_data = database.get_bin(bin_id)
    if not bin_data:
        return jsonify({"error": "Bin not found"}), 404
    return jsonify(bin_data)


@app.route("/api/bins/<int:bin_id>/history", methods=["GET"])
def api_bin_history(bin_id):
    limit = request.args.get("limit", default=20, type=int)
    return jsonify(database.get_bin_history(bin_id, limit=limit))


@app.route("/api/bins/<int:bin_id>/collect", methods=["POST"])
def api_collect_bin(bin_id):
    database.collect_bin(bin_id)
    return jsonify(database.get_bin(bin_id))


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Manually trigger one IoT sensor tick (handy for demos)."""
    database.simulate_sensor_tick()
    return jsonify(database.get_all_bins())


# ---------------------------------------------------------------------
# AI Waste Scanner
# ---------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def api_upload():
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400

    file = request.files["image"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    save_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(save_path)

    try:
        result = ai_helper.classify_waste_image(save_path)
    except Exception as e:
        return jsonify({"error": f"AI classification failed: {str(e)}"}), 500

    updated_bin = database.update_bin_after_waste(
        category=result["category"],
        item_name=result["item"],
        confidence=result["confidence"],
    )

    return jsonify({
        "item": result["item"],
        "category": result["category"],
        "confidence": result["confidence"],
        "tip": result["tip"],
        "bin": updated_bin,  # None when category is "Others" (no physical bin)
    })


# ---------------------------------------------------------------------
# Analytics (Weekly Summary, Waste Distribution, Weekly Trend, Alerts)
# ---------------------------------------------------------------------

@app.route("/api/summary", methods=["GET"])
def api_summary():
    return jsonify(database.get_weekly_summary())


@app.route("/api/distribution", methods=["GET"])
def api_distribution():
    return jsonify(database.get_waste_distribution())


@app.route("/api/trend", methods=["GET"])
def api_trend():
    return jsonify(database.get_weekly_trend())


@app.route("/api/notifications", methods=["GET"])
def api_notifications():
    return jsonify(database.get_notifications())


if __name__ == "__main__":
    app.run(debug=True, port=5000)