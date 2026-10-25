import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "revision_agent.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        confidence TEXT DEFAULT 'Medium',
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        score INTEGER,
        feedback TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    )
    """)

    conn.commit()
    conn.close()

def save_session(topic, difficulty, notes, flashcards):
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO sessions (topic, difficulty, notes) VALUES (?, ?, ?)",
        (topic, difficulty, notes)
    )
    session_id = cursor.lastrowid
    
    for card in flashcards:
        cursor.execute(
            "INSERT INTO flashcards (session_id, question, answer, confidence) VALUES (?, ?, ?, ?)",
            (session_id, card.get("question", ""), card.get("answer", ""), "Medium")
        )
        
    conn.commit()
    conn.close()
    return session_id

def update_flashcard_confidence(card_id, confidence):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE flashcards SET confidence = ? WHERE id = ?",
        (confidence, card_id)
    )
    conn.commit()
    conn.close()

def save_quiz_result(session_id, score, feedback):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO quiz_results (session_id, score, feedback) VALUES (?, ?, ?)",
        (session_id, score, feedback)
    )
    conn.commit()
    conn.close()

def get_analytics():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total_sessions FROM sessions")
    total_sessions = cursor.fetchone()["total_sessions"]
    
    cursor.execute("SELECT COUNT(*) as total_cards FROM flashcards")
    total_cards = cursor.fetchone()["total_cards"]
    
    cursor.execute("SELECT AVG(score) as avg_score FROM quiz_results")
    avg_score_row = cursor.fetchone()["avg_score"]
    avg_score = round(avg_score_row, 1) if avg_score_row is not None else 0
    
    cursor.execute("SELECT confidence, COUNT(*) as count FROM flashcards GROUP BY confidence")
    confidence_counts = {row["confidence"]: row["count"] for row in cursor.fetchall()}
    
    conn.close()
    return {
        "total_sessions": total_sessions,
        "total_cards": total_cards,
        "avg_score": avg_score,
        "easy_cards": confidence_counts.get("Easy", 0),
        "medium_cards": confidence_counts.get("Medium", 0),
        "hard_cards": confidence_counts.get("Hard", 0)
    }

init_db()
