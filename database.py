"""
database.py
Handles all SQLite storage for EcoSort AI:
 - Smart bins (id, type, fill level, temperature, status, last_collected)
 - Waste log (every classified item, for weekly analytics)
"""

import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ecosort.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist and seed 4 demo bins."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bins (
            id INTEGER PRIMARY KEY,
            waste_type TEXT NOT NULL,
            fill_level INTEGER NOT NULL DEFAULT 0,
            temperature REAL NOT NULL DEFAULT 25.0,
            status TEXT NOT NULL DEFAULT 'OK',
            last_collected TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS waste_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bin_id INTEGER,
            waste_type TEXT NOT NULL,
            category TEXT NOT NULL,
            confidence REAL,
            weight_kg REAL DEFAULT 0.4,
            timestamp TEXT NOT NULL
        )
    """)

    # Seed demo bins only if table is empty
    cur.execute("SELECT COUNT(*) AS c FROM bins")
    if cur.fetchone()["c"] == 0:
        demo_bins = [
            (1, "Plastic", 45, 27.0, "OK"),
            (2, "Organic", 78, 30.5, "Nearly Full"),
            (3, "Hazardous", 95, 33.0, "Critical"),
            (4, "E-Waste", 20, 24.0, "OK"),
        ]
        now = datetime.now().isoformat()
        cur.executemany(
            "INSERT INTO bins (id, waste_type, fill_level, temperature, status, last_collected) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(b[0], b[1], b[2], b[3], b[4], now) for b in demo_bins],
        )

    conn.commit()
    conn.close()


def get_all_bins():
    conn = get_connection()
    bins = conn.execute("SELECT * FROM bins ORDER BY id").fetchall()
    conn.close()
    return [dict(b) for b in bins]


def get_bin(bin_id):
    conn = get_connection()
    b = conn.execute("SELECT * FROM bins WHERE id = ?", (bin_id,)).fetchone()
    conn.close()
    return dict(b) if b else None


def _status_from_fill(fill_level):
    if fill_level >= 90:
        return "Critical"
    if fill_level >= 75:
        return "Nearly Full"
    return "OK"


def update_bin_after_waste(category, weight_kg=0.4):
    """
    Finds the bin matching `category` (e.g. 'Plastic', 'Organic',
    'Hazardous', 'E-Waste'), bumps its fill level, and logs the event.
    Returns the updated bin as a dict, or None if no matching bin exists.
    """
    conn = get_connection()
    cur = conn.cursor()

    bin_row = cur.execute(
        "SELECT * FROM bins WHERE waste_type = ?", (category,)
    ).fetchone()

    if not bin_row:
        conn.close()
        return None

    new_fill = min(100, bin_row["fill_level"] + 1)
    new_status = _status_from_fill(new_fill)

    cur.execute(
        "UPDATE bins SET fill_level = ?, status = ? WHERE id = ?",
        (new_fill, new_status, bin_row["id"]),
    )

    cur.execute(
        "INSERT INTO waste_log (bin_id, waste_type, category, confidence, weight_kg, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (bin_row["id"], category, category, None, weight_kg, datetime.now().isoformat()),
    )

    conn.commit()
    updated = dict(cur.execute("SELECT * FROM bins WHERE id = ?", (bin_row["id"],)).fetchone())
    conn.close()
    return updated


def collect_bin(bin_id):
    """Empty a bin (fill level -> 0) and reset its status."""
    conn = get_connection()
    conn.execute(
        "UPDATE bins SET fill_level = 0, status = 'OK', last_collected = ? WHERE id = ?",
        (datetime.now().isoformat(), bin_id),
    )
    conn.commit()
    conn.close()


def simulate_sensor_tick():
    """
    Simulates one IoT sensor reading cycle across all bins:
    fill level creeps up slightly, temperature drifts randomly.
    Meant to be called on a timer (see app.py's background thread).
    """
    import random

    conn = get_connection()
    cur = conn.cursor()
    bins = cur.execute("SELECT * FROM bins").fetchall()

    for b in bins:
        fill_delta = random.randint(0, 2)
        new_fill = min(100, b["fill_level"] + fill_delta)
        temp_delta = round(random.uniform(-0.5, 0.5), 1)
        new_temp = round(max(15.0, min(45.0, b["temperature"] + temp_delta)), 1)
        new_status = _status_from_fill(new_fill)

        cur.execute(
            "UPDATE bins SET fill_level = ?, temperature = ?, status = ? WHERE id = ?",
            (new_fill, new_temp, new_status, b["id"]),
        )

    conn.commit()
    conn.close()


def get_weekly_analytics():

    """
    Aggregates waste_log into per-category totals and overall stats.
    CO2 savings is a simple demo estimate: 0.5 kg CO2 saved per kg recycled
    (plastic/organic/e-waste), hazardous doesn't count as "saved".
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, COUNT(*) as items, SUM(weight_kg) as total_kg "
        "FROM waste_log GROUP BY category"
    ).fetchall()
    conn.close()

    breakdown = {r["category"]: {"items": r["items"], "kg": round(r["total_kg"] or 0, 2)} for r in rows}

    total_kg = sum(v["kg"] for v in breakdown.values())
    recyclable_kg = sum(
        v["kg"] for k, v in breakdown.items() if k in ("Plastic", "Organic", "E-Waste")
    )
    recycling_rate = round((recyclable_kg / total_kg) * 100, 1) if total_kg else 0
    co2_saved = round(recyclable_kg * 0.5, 1)

    return {
        "breakdown": breakdown,
        "total_kg": round(total_kg, 2),
        "recycling_rate": recycling_rate,
        "co2_saved_kg": co2_saved,
    }