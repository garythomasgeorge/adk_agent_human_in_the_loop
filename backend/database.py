import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

DB_NAME = "chat_history.db"

def init_db():
    """Initialize the database with necessary tables."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # Create messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            sender TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def save_chat_session(session_id: str, client_id: str, messages: List[Dict], status: str = "completed"):
    """Save a completed chat session and its messages."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check if session exists, if not create it
    c.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
    if not c.fetchone():
        start_time = messages[0]['timestamp'] if messages else datetime.now().isoformat()
        c.execute(
            "INSERT INTO sessions (id, client_id, start_time, status) VALUES (?, ?, ?, ?)",
            (session_id, client_id, start_time, "active")
        )
    
    # Update session status and end time
    end_time = datetime.now().isoformat()
    c.execute(
        "UPDATE sessions SET end_time = ?, status = ? WHERE id = ?",
        (end_time, status, session_id)
    )
    
    # Save messages
    # First, clear existing messages for this session to avoid duplicates if re-saving
    c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    
    for msg in messages:
        c.execute(
            "INSERT INTO messages (session_id, sender, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, msg['sender'], msg['content'], msg.get('timestamp', datetime.now().isoformat()))
        )
        
    conn.commit()
    conn.close()

def get_all_sessions() -> List[Dict]:
    """Retrieve all chat sessions."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM sessions ORDER BY start_time DESC")
    rows = c.fetchall()
    
    sessions = []
    for row in rows:
        sessions.append(dict(row))
        
    conn.close()
    return sessions

def get_session_details(session_id: str) -> Dict:
    """Retrieve details and messages for a specific session."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    session_row = c.fetchone()
    
    if not session_row:
        conn.close()
        return None
        
    session = dict(session_row)
    
    c.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    message_rows = c.fetchall()
    
    messages = [dict(row) for row in message_rows]
    session['messages'] = messages
    
    conn.close()
    return session
