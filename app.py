import json
import urllib.request
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from calendar_config import MEDEA_CALENDAR_ID
from keep_config import NOTE_ID
from done_db import init_db, is_done, set_done, clean_old

# Motivi di preghiera - file semplice modificabile da browser
MOTIVI_FILE = 'motivi.txt'

def read_motivi():
    try:
        with open(MOTIVI_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return 'Pace per la famiglia\nGrazie per la giornata\nSalute e serenità'

app = Flask(__name__)
init_db()
TODAY_STR = datetime.now().strftime('%Y-%m-%d')
clean_old(TODAY_STR)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/keep']

def fetch_calendar_events():
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.now()
        # Solo eventi di oggi (da mezzanotte a mezzanotte domani)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow += __import__('datetime').timedelta(days=1)
        time_min = now.strftime('%Y-%m-%dT00:00:00Z')
        time_max = tomorrow.strftime('%Y-%m-%dT00:00:00Z')
        events = []
        for cal_id, name in [('luca.buccheri.92@gmail.com', 'Luca'), (MEDEA_CALENDAR_ID, 'Medea')]:
            try:
                res = service.events().list(
                    calendarId=cal_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    maxResults=10,
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                for item in res.get('items', []):
                    events.append({
                        'id': item['id'],
                        'title': f"[{name}] {item['summary']}",
                        'done': is_done(item['id'], TODAY_STR),
                        'time': item['start'].get('dateTime', item['start'].get('date'))[11:16],
                    })
            except Exception:
                pass
        # Se vuoto, mantiene placeholder
        return events[:5]
    except Exception:
        return []


def fetch_keep_notes():
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', scopes=SCOPES)
        service = build('keep', 'v1', credentials=creds)
        res = service.notes().get(name=f"notes/{NOTE_ID}").execute()
        # Estrae testo (lista o blocchi)
        body = res.get('body', {})
        text_parts = []
        if 'text' in body:
            text_parts.append(body['text'].get('text', ''))
        if 'list' in body:
            for item in body['list'].get('listItems', []):
                item_text = item.get('text', {}).get('text', '')
                if item_text:
                    text_parts.append('• ' + item_text)
        note_text = '\n'.join(p for p in text_parts if p)
        if not note_text.strip():
            note_text = res.get('title', 'Nota preghiera')
        return note_text
    except Exception as e:
        return f"Nota non accessibile: condivide con dashboard-casa@...? ({type(e).__name__})"

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


@app.route("/update_motivi", methods=["POST"])
def update_motivi():
    data = request.form.get('motivi', '')
    with open(MOTIVI_FILE, 'w', encoding='utf-8') as f:
        f.write(data)
    return "OK"

@app.route("/")
def index():
    mesi = ['', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
            'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']
    giorni = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
    now = datetime.now()
    today = f"{giorni[now.weekday()]} {now.day}/{now.month}/{now.year}"
    current_time = datetime.now().strftime("%H:%M")
    weather = fetch_weather()
    prayer_text = read_motivi()
    is_thursday = datetime.now().weekday() == 3
    deadlines = fetch_calendar_events()
    return render_template(
        "index.html",
        today=today,
        current_time=current_time,
        weather=weather,
        is_thursday=is_thursday,
        deadlines=deadlines,
        prayer_text=prayer_text,
    )


@app.route("/toggle_deadline/<event_id>", methods=["POST"])
def toggle_deadline(event_id):
    today_str = datetime.now().strftime('%Y-%m-%d')
    done = not is_done(event_id, today_str)
    set_done(event_id, today_str, done)
    return jsonify({"done": done})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
