"""
database.py
SQLite storage for EcoSort AI, matching the dashboard design:
 - Smart bins: id, name, waste_type, fill_level, temperature, status, location
 - Waste log: every classified item (for weekly summary / trend / distribution)
 - Notifications: derived from bin status (no separate table needed)

Categories used throughout: Plastic, Organic, E-Waste, Hazardous, Others.
"Others" is anything the AI scanner can't map to a physical smart bin
(e.g. mixed/general waste) - it still counts in the waste distribution
pie chart, matching the dashboard's "Others 35.4%" slice.
"""

import sqlite3
import random
from datetime import datetime, timedelta
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ecosort.db")

CATEGORIES = ["Plastic", "Organic", "E-Waste", "Hazardous", "Others"]
# Categories that count toward "recycled" / CO2 saved in the summary cards
RECYCLABLE_CATEGORIES = {"Plastic", "Organic", "E-Waste"}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _status_from_fill(fill_level):
    if fill_level >= 90:
        return "Critical"
    if fill_level >= 75:
        return "Nearly Full"
    if fill_level >= 50:
        return "Half Full"
    return "Low"


def _migrate_schema(cur, conn):
    """
    Adds any columns that a pre-existing ecosort.db might be missing
    (e.g. an old waste_log table from before item_name/confidence were
    added, or an old bins table from before name/location existed).
    Safe to run every startup - it's a no-op once columns already exist.
    """
    expected_columns = {
        "bins": {
            "name": "TEXT NOT NULL DEFAULT 'Unnamed Bin'",
            "location": "TEXT NOT NULL DEFAULT 'Unassigned'",
        },
        "waste_log": {
            "item_name": "TEXT",
            "confidence": "REAL",
        },
    }

    for table, columns in expected_columns.items():
        existing = {row["name"] for row in cur.execute(f"PRAGMA table_info({table})")}
        for col_name, col_def in columns.items():
            if col_name not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")

    conn.commit()


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bins (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            waste_type TEXT NOT NULL,
            fill_level INTEGER NOT NULL DEFAULT 0,
            temperature REAL NOT NULL DEFAULT 25.0,
            status TEXT NOT NULL DEFAULT 'Low',
            location TEXT NOT NULL DEFAULT 'Unassigned',
            last_collected TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS waste_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bin_id INTEGER,
            category TEXT NOT NULL,
            item_name TEXT,
            confidence REAL,
            weight_kg REAL DEFAULT 0.4,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()

    _migrate_schema(cur, conn)

    # Seed demo bins to match the dashboard mock (Bin 1-4)
    cur.execute("SELECT COUNT(*) AS c FROM bins")
    if cur.fetchone()["c"] == 0:
        now = datetime.now().isoformat()
        demo_bins = [
            (1, "Plastic Waste Bin", "Plastic", 80, 29.0, "Nearly Full", "Block A - Floor 1"),
            (2, "Organic Waste Bin", "Organic", 55, 28.0, "Half Full", "Block A - Floor 1"),
            (3, "E-Waste Bin", "E-Waste", 75, 27.0, "Almost Full", "Block B - Floor 2"),
            (4, "Hazardous Waste Bin", "Hazardous", 20, 26.0, "Low", "Block B - Floor 1"),
        ]
        cur.executemany(
            "INSERT INTO bins (id, name, waste_type, fill_level, temperature, status, location, last_collected) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [(b[0], b[1], b[2], b[3], b[4], b[5], b[6], now) for b in demo_bins],
        )
        conn.commit()

    conn.close()

    # Seed two weeks of demo waste history so the summary/trend/distribution
    # charts aren't empty on first run.
    _seed_demo_history_if_empty()


def _seed_demo_history_if_empty():
    conn = get_connection()
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) AS c FROM waste_log").fetchone()["c"]
    if count > 0:
        conn.close()
        return

    # Roughly matches the dashboard: this week totals ~420/280/90/40/454 kg
    # (Plastic/Organic/E-Waste/Hazardous/Others), last week a bit lower so
    # the % change cards show the same up/down direction as the mock.
    this_week_targets = {"Plastic": 420, "Organic": 280, "E-Waste": 90, "Hazardous": 40, "Others": 454}
    last_week_targets = {"Plastic": 356, "Organic": 250, "E-Waste": 86, "Hazardous": 41, "Others": 420}

    bin_by_category = {b["waste_type"]: b["id"] for b in get_all_bins()}

    rows = []
    today = datetime.now()

    def spread_across_week(category, total_kg, week_start_offset_days):
        # Split a week's total into ~21 random log entries across 7 days,
        # weighted a bit heavier toward the end of the week (Fri/Sat/Sun)
        # to mirror the rising trend line in the dashboard mock.
        day_weights = [0.10, 0.12, 0.13, 0.14, 0.18, 0.16, 0.17]  # Mon..Sun
        entries_per_day = 3
        for day_idx, weight in enumerate(day_weights):
            day_total = total_kg * weight
            per_entry = round(day_total / entries_per_day, 2)
            day_date = today - timedelta(days=week_start_offset_days + (6 - day_idx))
            for _ in range(entries_per_day):
                jittered = max(0.1, round(per_entry * random.uniform(0.8, 1.2), 2))
                ts = day_date.replace(
                    hour=random.randint(7, 20), minute=random.randint(0, 59)
                ).isoformat()
                rows.append((bin_by_category.get(category), category, None, None, jittered, ts))

    for category, kg in this_week_targets.items():
        spread_across_week(category, kg, week_start_offset_days=0)
    for category, kg in last_week_targets.items():
        spread_across_week(category, kg, week_start_offset_days=7)

    cur.executemany(
        "INSERT INTO waste_log (bin_id, category, item_name, confidence, weight_kg, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Bins
# ---------------------------------------------------------------------

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


def get_bin_history(bin_id, limit=20):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM waste_log WHERE bin_id = ? ORDER BY timestamp DESC LIMIT ?",
        (bin_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_bin_after_waste(category, weight_kg=0.4, item_name=None, confidence=None):
    """
    Logs a waste event. If `category` maps to a physical bin, bumps its
    fill level/status too. "Others" (or any category without a bin) is
    still logged for analytics but doesn't touch a physical bin.
    Returns the updated bin dict, or None if no matching bin exists.
    """
    conn = get_connection()
    cur = conn.cursor()

    bin_row = cur.execute(
        "SELECT * FROM bins WHERE waste_type = ?", (category,)
    ).fetchone()

    updated_bin = None
    if bin_row:
        new_fill = min(100, bin_row["fill_level"] +max(1,int(weight_kg*5)))
        new_status = _status_from_fill(new_fill)
        cur.execute(
            "UPDATE bins SET fill_level = ?, status = ? WHERE id = ?",
            (new_fill, new_status, bin_row["id"]),
        )
        updated_bin = dict(cur.execute(
            "SELECT * FROM bins WHERE id = ?", (bin_row["id"],)
        ).fetchone())

    cur.execute(
        "INSERT INTO waste_log (bin_id, category, item_name, confidence, weight_kg, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (bin_row["id"] if bin_row else None, category, item_name, confidence, weight_kg,
         datetime.now().isoformat()),
    )

    conn.commit()
    conn.close()
    return updated_bin


def collect_bin(bin_id):
    conn = get_connection()
    conn.execute(
        "UPDATE bins SET fill_level = 0, status = 'Low', last_collected = ? WHERE id = ?",
        (datetime.now().isoformat(), bin_id),
    )
    conn.commit()
    conn.close()


def simulate_sensor_tick():
    """Fake IoT sensor push: nudges fill level and temperature on all bins."""
    conn = get_connection()
    cur = conn.cursor()
    bins = cur.execute("SELECT * FROM bins").fetchall()

    for b in bins:
        new_fill = min(100, b["fill_level"] + random.randint(0, 2))
        new_temp = round(max(15.0, min(45.0, b["temperature"] + random.uniform(-0.5, 0.5))), 1)
        new_status = _status_from_fill(new_fill)
        cur.execute(
            "UPDATE bins SET fill_level = ?, temperature = ?, status = ? WHERE id = ?",
            (new_fill, new_temp, new_status, b["id"]),
        )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------
# Dashboard analytics: summary cards, distribution pie, weekly trend
# ---------------------------------------------------------------------

def _sum_by_category(start, end):
    """Returns {category: kg} for waste_log rows between two ISO timestamps."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT category, SUM(weight_kg) AS kg FROM waste_log "
        "WHERE timestamp >= ? AND timestamp < ? GROUP BY category",
        (start, end),
    ).fetchall()
    conn.close()
    return {r["category"]: round(r["kg"] or 0, 1) for r in rows}


def get_weekly_summary():
    """
    Powers the top "Weekly Summary" cards: kg total + % change vs last
    week, for each category, plus overall Total Waste and CO2 Saved.
    """
    now = datetime.now()
    this_week_start = (now - timedelta(days=7)).isoformat()
    last_week_start = (now - timedelta(days=14)).isoformat()

    this_week = _sum_by_category(this_week_start, now.isoformat())
    last_week = _sum_by_category(last_week_start, this_week_start)

    cards = {}
    for cat in CATEGORIES:
        current = this_week.get(cat, 0)
        previous = last_week.get(cat, 0)
        if previous > 0:
            pct_change = round(((current - previous) / previous) * 100, 1)
        else:
            pct_change = 100.0 if current > 0 else 0.0
        cards[cat] = {"kg": current, "pct_change": pct_change}

    total_kg = round(sum(v["kg"] for v in cards.values()), 1)
    recyclable_kg = round(sum(v["kg"] for k, v in cards.items() if k in RECYCLABLE_CATEGORIES), 1)
    co2_saved = round(recyclable_kg * 0.5, 1)

    return {
        "categories": cards,
        "total_kg": total_kg,
        "co2_saved_kg": co2_saved,
    }


def get_waste_distribution():
    """Powers the 'Waste Distribution' pie chart: kg + % share per category."""
    now = datetime.now()
    this_week_start = (now - timedelta(days=7)).isoformat()
    this_week = _sum_by_category(this_week_start, now.isoformat())

    total_kg = sum(this_week.values()) or 1  # avoid div by zero
    distribution = []
    for cat in CATEGORIES:
        kg = this_week.get(cat, 0)
        distribution.append({
            "category": cat,
            "kg": round(kg, 1),
            "pct": round((kg / total_kg) * 100, 1),
        })
    return distribution


def get_weekly_trend():
    """
    Powers the 'Weekly Trend' line chart: total kg logged per day for
    the last 7 days, labeled Mon..Sun.
    """
    conn = get_connection()
    today = datetime.now().date()
    trend = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = day.isoformat()
        day_end = (day + timedelta(days=1)).isoformat()
        row = conn.execute(
            "SELECT SUM(weight_kg) AS kg FROM waste_log WHERE timestamp >= ? AND timestamp < ?",
            (day_start, day_end),
        ).fetchone()
        trend.append({
            "label": day.strftime("%a"),  # Mon, Tue, ...
            "date": day_start,
            "kg": round(row["kg"] or 0, 1),
        })
    conn.close()
    return trend


def get_notifications():
    """
    Powers the bell icon badge: one notification per bin that needs
    attention (Nearly Full / Almost Full / Critical).
    """
    alert_statuses = {"Nearly Full", "Almost Full", "Critical"} 
    conn = get_connection()
    bins = conn.execute("SELECT * FROM bins").fetchall()
    conn.close()

    alerts = []
    for b in bins:
        if b["status"] in alert_statuses:
            alerts.append({
                "bin_id": b["id"],
                "name": b["name"],
                "message": f"{b['name']} is {b['fill_level']}% full ({b['status']})",
                "status": b["status"],
            })
    return {"count": len(alerts), "alerts": alerts}