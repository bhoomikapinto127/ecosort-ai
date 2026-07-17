"""
app.py
Flask backend for EcoSort AI.

Routes:
    GET  /                  -> dashboard page
    GET  /api/bins          -> list all bins
    POST /api/bins/<id>/collect -> empty a bin
    POST /api/upload        -> upload waste image, classify with Groq, update bin
    GET  /api/analytics     -> weekly analytics summary

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
#import ai_helper

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
# (Flask's debug reloader spawns a child process flagged with
# WERKZEUG_RUN_MAIN, so we only start the thread in the real worker.)
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    threading.Thread(target=iot_simulator_loop, daemon=True).start()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/bins", methods=["GET"])
def api_get_bins():
    return jsonify(database.get_all_bins())


@app.route("/api/bins/<int:bin_id>/collect", methods=["POST"])
def api_collect_bin(bin_id):
    database.collect_bin(bin_id)
    return jsonify(database.get_bin(bin_id))


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

    updated_bin = database.update_bin_after_waste(result["category"])

    return jsonify({
        "item": result["item"],
        "category": result["category"],
        "confidence": result["confidence"],
        "tip": result["tip"],
        "bin": updated_bin,
    })


@app.route("/api/simulate", methods=["POST"])
def api_simulate():
    """Manually trigger one IoT sensor tick (handy for demos)."""
    database.simulate_sensor_tick()
    return jsonify(database.get_all_bins())


@app.route("/api/analytics", methods=["GET"])

def api_analytics():
    return jsonify(database.get_weekly_analytics())


if __name__ == "__main__":
    app.run(debug=True, port=5000)

