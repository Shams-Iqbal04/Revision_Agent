import os
import json
import sqlite3
from typing import Optional, Dict, Any
from langchain_core.messages import messages_to_dict, messages_from_dict


class CheckpointDB:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "checkpoints.db")
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_checkpoints (
                    session_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    difficulty TEXT NOT NULL,
                    doc_text TEXT,
                    questions_answered INTEGER DEFAULT 0,
                    is_concluded INTEGER DEFAULT 0,
                    messages_json TEXT,
                    action_history_json TEXT,
                    student_answers_json TEXT,
                    doubt_history_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def save_checkpoint(self, session: Any):
        """Persist the full session state into SQLite atomically."""
        try:
            msgs_dict = messages_to_dict(session.messages) if getattr(session, "messages", None) else []

            actions_clean = []
            for act in getattr(session, "action_history", []):
                resp_dict = None
                if "response" in act and hasattr(act["response"], "content"):
                    try:
                        resp_dict = messages_to_dict([act["response"]])[0]
                    except Exception:
                        resp_dict = None
                actions_clean.append({
                    "content": act.get("content", ""),
                    "tool_calls": act.get("tool_calls", []),
                    "response_dict": resp_dict
                })

            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO session_checkpoints (
                        session_id, topic, difficulty, doc_text,
                        questions_answered, is_concluded,
                        messages_json, action_history_json,
                        student_answers_json, doubt_history_json,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(session_id) DO UPDATE SET
                        topic=excluded.topic,
                        difficulty=excluded.difficulty,
                        doc_text=excluded.doc_text,
                        questions_answered=excluded.questions_answered,
                        is_concluded=excluded.is_concluded,
                        messages_json=excluded.messages_json,
                        action_history_json=excluded.action_history_json,
                        student_answers_json=excluded.student_answers_json,
                        doubt_history_json=excluded.doubt_history_json,
                        updated_at=CURRENT_TIMESTAMP
                """, (
                    session.id,
                    session.topic,
                    session.difficulty,
                    session.doc_text,
                    session.questions_answered,
                    1 if session.is_concluded else 0,
                    json.dumps(msgs_dict),
                    json.dumps(actions_clean),
                    json.dumps(getattr(session, "student_answers", [])),
                    json.dumps(getattr(session, "doubt_history", [])),
                ))
                conn.commit()
        except Exception as e:
            print(f"[CheckpointDB] Error saving checkpoint for {getattr(session, 'id', 'unknown')}: {e}")

    def load_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the persisted state for session_id."""
        try:
            with self._get_connection() as conn:
                cur = conn.execute(
                    "SELECT * FROM session_checkpoints WHERE session_id = ?",
                    (session_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None

                msgs = []
                if row["messages_json"]:
                    try:
                        msgs = messages_from_dict(json.loads(row["messages_json"]))
                    except Exception:
                        pass

                raw_actions = json.loads(row["action_history_json"]) if row["action_history_json"] else []
                actions = []
                for act in raw_actions:
                    resp_obj = None
                    if act.get("response_dict"):
                        try:
                            resp_obj = messages_from_dict([act["response_dict"]])[0]
                        except Exception:
                            pass
                    actions.append({
                        "content": act.get("content", ""),
                        "tool_calls": act.get("tool_calls", []),
                        "response": resp_obj
                    })

                return {
                    "id": row["session_id"],
                    "topic": row["topic"],
                    "difficulty": row["difficulty"],
                    "doc_text": row["doc_text"],
                    "questions_answered": row["questions_answered"],
                    "is_concluded": bool(row["is_concluded"]),
                    "messages": msgs,
                    "action_history": actions,
                    "student_answers": json.loads(row["student_answers_json"]) if row["student_answers_json"] else [],
                    "doubt_history": json.loads(row["doubt_history_json"]) if row["doubt_history_json"] else [],
                    "updated_at": row["updated_at"]
                }
        except Exception as e:
            print(f"[CheckpointDB] Error loading checkpoint for {session_id}: {e}")
            return None

    def delete_checkpoint(self, session_id: str):
        """Remove checkpoint when session is cleared or reset."""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM session_checkpoints WHERE session_id = ?",
                    (session_id,)
                )
                conn.commit()
        except Exception as e:
            print(f"[CheckpointDB] Error deleting checkpoint for {session_id}: {e}")
