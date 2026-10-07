import sqlite3
from datetime import datetime

DB = 'done_events.db'

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute('CREATE TABLE IF NOT EXISTS done (event_id TEXT PRIMARY KEY, event_date TEXT, done INTEGER)')
    conn.commit()
    conn.close()

def is_done(event_id, today_str):
    conn = sqlite3.connect(DB)
    row = conn.execute('SELECT done FROM done WHERE event_id=? AND event_date=?', (event_id, today_str)).fetchone()
    conn.close()
    return bool(row[0]) if row else False

def set_done(event_id, today_str, done):
    conn = sqlite3.connect(DB)
    conn.execute('INSERT OR REPLACE INTO done VALUES (?,?,?)', (event_id, today_str, 1 if done else 0))
    conn.commit()
    conn.close()

def clean_old(today_str):
    conn = sqlite3.connect(DB)
    conn.execute('DELETE FROM done WHERE event_date != ?', (today_str,))
    conn.commit()
    conn.close()
