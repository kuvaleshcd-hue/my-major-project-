import sqlite3
import os
from datetime import datetime

DB_FILE = "history.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_name TEXT,
            source_lang TEXT,
            target_lang TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            video_path TEXT,
            audio_path TEXT,
            srt_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_job(video_name: str, source_lang: str, target_lang: str, video_path: str, audio_path: str, srt_path: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO history (video_name, source_lang, target_lang, video_path, audio_path, srt_path)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (video_name, source_lang, target_lang, video_path, audio_path, srt_path))
    conn.commit()
    conn.close()

def get_history():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT id, video_name, source_lang, target_lang, timestamp, video_path, audio_path, srt_path 
        FROM history 
        ORDER BY timestamp DESC
    ''')
    rows = c.fetchall()
    conn.close()
    
    keys = ["id", "video_name", "source_lang", "target_lang", "timestamp", "video_path", "audio_path", "srt_path"]
    return [dict(zip(keys, row)) for row in rows]
