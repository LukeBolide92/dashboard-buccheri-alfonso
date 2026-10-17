import json
import urllib.request
from datetime import datetime, timedelta, timezone
import openpyxl
from flask import Flask, render_template, jsonify, request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from calendar_config import MEDEA_CALENDAR_ID, LUCA_CALENDAR_ID

# Motivi di preghiera - file semplice modificabile da browser
MOTIVI_FILE = 'motivi.txt'

def read_motivi():
    try:
        with open(MOTIVI_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return 'Pace per la famiglia\nGrazie per la giornata\nSalute e serenità'

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/keep']
app = Flask(__name__)

def fetch_calendar_events():
    try:
        creds = service_account.Credentials.from_service_account_file(
            'service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.now()
        # Solo eventi di oggi (da mezzanotte a mezzanotte domani)
        tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow += timedelta(days=1)
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
                        'done': False,
                        'time': item['start'].get('dateTime', item['start'].get('date'))[11:16],
                    })
            except Exception:
                pass
        return events[:5]
    except Exception:
        return []


def fetch_keep_notes():
    try:
        with open('motivi.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Nota non disponibile ({type(e).__name__})"

CARDANO_LAT = 45.68
CARDANO_LON = 8.82


def fetch_weather():
    """Fetch weather from Open-Meteo for Cardano al Campo."""
    try:
        lat, lon = CARDANO_LAT, CARDANO_LON
        
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={CARDANO_LAT}"
            f"&longitude={CARDANO_LON}"
            f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
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
            "wind": current.get("wind_speed_10m"),
            "city": "Cardano al Campo",
        }
    except Exception as e:
        return {"temp": None, "icon": "❓", "desc": "Impossibile caricare il meteo", "city": "Milano"}


@app.route("/toggle_deadline/<event_id>", methods=["POST"])


@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.route("/api/weather")
def api_weather(): return jsonify(fetch_weather())


@app.route("/api/versetto")
def api_versetto():
    try:
        import requests, datetime
        with open('youversion_key.json') as f:
            key = json.load(f).get('key', '')
        today = datetime.datetime.now().timetuple().tm_yday
        url = f"https://api.youversion.com/v1/verse-of-the-days/{today}"
        resp = requests.get(url, headers={"X-YVP-App-Key": key}, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Il versetto del giorno può essere diretto o dentro data
        if isinstance(data, dict) and "passage_id" in data:
            passage_id = data.get("passage_id")
        else:
            passage = data.get("data", {}) if isinstance(data, dict) else {}
            if isinstance(passage, list) and passage:
                passage = passage[0]
            passage_id = passage.get("passage_id") if isinstance(passage, dict) else None
        if passage_id:
            # Bibbia italiana: prova con ID comune; se sbagliato, cambia
            bib_url = f"https://api.youversion.com/v1/bibles/1932/passages/{passage_id}"
            bib_resp = requests.get(bib_url, headers={"X-YVP-App-Key": key}, timeout=10)
            if bib_resp.status_code == 200:
                return jsonify(bib_resp.json())
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/api/motivi")
def api_motivi(): return jsonify({"motivi": read_motivi()})


@app.route("/api/calendar-events")
def api_calendar_events():
    try:
        m = int(request.args.get('month', datetime.now().month))
        y = int(request.args.get('year', datetime.now().year))
        start = datetime(y, m, 1, 0, 0, 0, tzinfo=timezone.utc)
        if m == 12:
            end = datetime(y+1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        else:
            end = datetime(y, m+1, 1, 0, 0, 0, tzinfo=timezone.utc)
        creds = service_account.Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        service = build('calendar', 'v3', credentials=creds)
        out = []
        for cal_id in [MEDEA_CALENDAR_ID, LUCA_CALENDAR_ID]:
            try:
                events_result = service.events().list(calendarId=cal_id, timeMin=start.isoformat(), timeMax=end.isoformat(), singleEvents=True, orderBy='startTime').execute()
                events = events_result.get('items', [])
                for ev in events:
                    start_ev = ev.get('start', {}).get('dateTime') or ev.get('start', {}).get('date')
                    summary = ev.get('summary', '')
                    day = int(start_ev[8:10]) if start_ev and len(start_ev) >= 10 else None
                    time_str = ''
                    if start_ev and 'T' in start_ev:
                        time_part = start_ev.split('T')[1]
                        time_str = time_part[:5]  # HH:MM
                    out.append({'date': start_ev[:10] if start_ev else None, 'day': day, 'summary': summary, 'time': time_str, 'source': cal_id})
            except Exception:
                pass

        return jsonify(out)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==============================
# NUOVO ENDPOINT: GIORNI GIOVANI
# ==============================
def read_giorni_giovani():
    """Legge il file Excel e restituisce gli eventi nel formato {date: 'YYYY-MM-DD', summary: '...'}"""
    try:
        # Carica l'Excel
        wb = openpyxl.load_workbook('programma_giovani/Programma Gruppo Giovani.xlsx', data_only=True)
        ws = wb.worksheets[0]  # Primo foglio
        
        # Trova le intestazioni (dove sono i mesi e i sabati)
        # Cerchiamo la cella che contiene "Sab" o "Sabato"
        header_row = None
        for row in ws.iter_rows(min_row=1, max_row=5, values_only=True):
            if any(cell and str(cell).strip().lower() in ['sab', 'sabato'] for cell in row):
                header_row = row
                break
        
        if not header_row:
            return []  # Nessun dato trovato
            
        # Trova l'indice della colonna "Sab"
        sab_index = None
        for i, cell in enumerate(header_row):
            if cell and str(cell).strip().lower() in ['sab', 'sabato']:
                sab_index = i
                break
                
        if sab_index is None:
            return []  # Nessuna colonna "Sab" trovata
            
        # Leggi le date
        events = []
        for row_idx in range(6, ws.max_row + 1):  # Partiamo dalla riga 6 (dopo le intestazioni)
            cell = ws.cell(row=row_idx, column=sab_index + 1)  # +1 per convertire da 0-based a 1-based
            if cell.value:
                # Estrai il numero del giorno (es. "1", "8", "15")
                # Il formato sembra essere solo il numero del giorno
                day_str = str(cell.value).strip()
                try:
                    day = int(day_str)
                except ValueError:
                    continue  # Salta se non è un numero
                    
                # Estrai il mese (dalla prima colonna della riga)
                month_cell = ws.cell(row=row_idx, column=1)
                month_name = str(month_cell.value).strip().capitalize()
                
                # Mappa il nome del mese al numero
                month_map = {
                    'Gen': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'Mag': 5, 'Giu': 6,
                    'Lug': 7, 'Ago': 8, 'Set': 9, 'Ott': 10, 'Nov': 11, 'Dic': 12
                }
                
                if month_name in month_map:
                    month = month_map[month_name]
                    year = 2026  # Supponiamo l'anno 2026
                    
                    # Costruisci la data ISO
                    date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
                    
                    # Leggi il titolo dell'evento (colonna a destra di "Sab")
                    title_cell = ws.cell(row=row_idx, column=sab_index + 2)  # +2 per andare alla colonna successiva
                    title = str(title_cell.value).strip() if title_cell.value else ""
                    
                    if title:
                        events.append({
                            'date': date_str,
                            'summary': title
                        })
        return events
    except Exception as e:
        print(f"Errore nella lettura dell'Excel: {e}")
        return []


@app.route("/api/giorni-giovani")
def api_giorni_giovani():
    try:
        events = read_giorni_giovani()
        return jsonify(events)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)