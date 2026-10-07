import json
import urllib.request
from datetime import datetime
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Placeholder deadlines for today (will be stored in data/deadlines.json)
try:
    with open("data/deadlines.json", "r", encoding="utf-8") as f:
        DEADLINES = json.load(f)
except Exception:
    DEADLINES = [
        {"id": 1, "title": "Pagare la bolletta della luce", "done": False, "time": "18:00"},
        {"id": 2, "title": "Ritirare la posta", "done": False, "time": "12:00"},
        {"id": 3, "title": "Chiamare la nonna", "done": False, "time": "20:00"},
    ]
    # ensure file exists
    import os
    os.makedirs("data", exist_ok=True)
    with open("data/deadlines.json", "w", encoding="utf-8") as f:
        json.dump(DEADLINES, f, ensure_ascii=False, indent=2)


CARDANO_LAT = 45.68
CARDANO_LON = 8.82


def fetch_weather():
    """Fetch weather from Open-Meteo for Cardano al Campo."""
    try:
        lat, lon = CARDANO_LAT, CARDANO_LON
        
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={CARDANO_LAT}"
            f"&longitude={CARDANO_LON}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code&timezone=auto"
        )
        with urllib.request.urlopen(url, timeout=10) as f:
            data = json.load(f)
        current = data["current"]
        code = current["weather_code"]
        icons = {
            0: ("☀️", "Sereno"),
            1: ("⛅", "Parzialmente nuvoloso"),
            2: ("⛅", "Nuvoloso"),
            3: ("☁️", "Coperto"),
            45: ("🌫", "Nebbia"),
            48: ("🌫", "Nebbia densa"),
            51: ("🌧", "Piovaschio leggero"),
            53: ("🌧", "Piovaschio"),
            55: ("🌧", "Piovaschio intenso"),
            56: ("🌧", "Pioggia leggera"),
            57: ("🌧", "Pioggia forte"),
            61: ("🌧", "Pioggia"),
            63: ("🌧", "Pioggia"),
            65: ("🌧", "Pioggia forte"),
            71: ("❄️", "Neve"),
            73: ("❄️", "Neve"),
            75: ("❄️", "Nevicate forti"),
            80: ("🌦", "Rovesci"),
            81: ("🌦", "Rovesci"),
            82: ("🌦", "Rovesci intensi"),
            85: ("❄️", "Nevicate"),
            86: ("❄️", "Nevicate forti"),
            95: ("⛈", "Temporale"),
            96: ("⛈", "Temporale con grandine"),
            99: ("⛈", "Temporale forte"),
        }
        icon, desc = icons.get(code, ("☁️", "Nuvoloso"))
        return {
            "temp": current["temperature_2m"],
            "icon": icon,
            "desc": desc,
            "humidity": current.get("relative_humidity_2m"),
            "city": "Cardano al Campo",
        }
    except Exception as e:
        return {"temp": None, "icon": "❓", "desc": "Impossibile caricare il meteo", "city": "Milano"}


@app.route("/")
def index():
    today = datetime.now().strftime("%A %d %B %Y")
    current_time = datetime.now().strftime("%H:%M")
    weather = fetch_weather()
    is_thursday = datetime.now().weekday() == 3
    return render_template(
        "index.html",
        today=today,
        current_time=current_time,
        weather=weather,
        is_thursday=is_thursday,
        deadlines=DEADLINES,
    )


@app.route("/toggle_deadline/<int:deadline_id>", methods=["POST"])
def toggle_deadline(deadline_id):
    deadline = next((d for d in DEADLINES if d["id"] == deadline_id), None)
    if deadline:
        deadline["done"] = not deadline["done"]
        # persist
        try:
            with open("data/deadlines.json", "w", encoding="utf-8") as f:
                json.dump(DEADLINES, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return jsonify({"done": deadline["done"]})
    return jsonify({"done": False}), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)