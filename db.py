import sqlite3
import os
from datetime import datetime
import hashlib

DB_FILE = "history.db"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username: str, password: str) -> bool:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return True
    return False

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
