import uuid
from typing import Dict, List, Any, Optional
from langchain_core.messages import HumanMessage, ToolMessage
from agent.tutor_agent import step_tutor


class Session:
    def __init__(self, topic: str, difficulty: str):
        self.id: str = str(uuid.uuid4())
        self.topic: str = topic
        self.difficulty: str = difficulty
        self.messages: list = []
        self.action_history: list = []
        self.student_answers: list = []
        self.doubt_history: list = []
        self.questions_answered: int = 0
        self.is_concluded: bool = False


class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create(self, topic: str, difficulty: str) -> Session:
        session = Session(topic, difficulty)
        self._sessions[session.id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def start(self, session_id: str) -> dict:
        session = self.get(session_id)
        if not session:
            raise ValueError("Session not found")

        start_msg = HumanMessage(
            content=(
                f"Hi, I want to revise {session.topic} at {session.difficulty} level. "
                f"Please start by calling give_revision_notes to give me comprehensive revision notes on this topic. "
                f"Do NOT ask any questions yet — I will tell you when I am ready for questions."
            )
        )
        session.messages.append(start_msg)

        res = step_tutor(
            session.messages,
            topic=session.topic,
            difficulty=session.difficulty,
        )
        session.messages.append(res["response"])
        session.action_history.append(res)

        return self._format_response(session, res)

    def respond(self, session_id: str, answer: str) -> dict:
        session = self.get(session_id)
        if not session:
            raise ValueError("Session not found")

        current_idx = len(session.action_history) - 1

        session.student_answers.append(
            {"answer": answer, "after_action_idx": current_idx}
        )

        latest = session.action_history[-1] if session.action_history else None
        latest_tools = latest.get("tool_calls", []) if latest else []

        if any(tc["name"] == "ask_question" for tc in latest_tools):
            session.questions_answered += 1

        for tc in latest_tools:
            session.messages.append(
                ToolMessage(content="Action presented to student.", tool_call_id=tc["id"])
            )

        session.messages.append(HumanMessage(content=answer))

        res = step_tutor(
            session.messages,
            topic=session.topic,
            difficulty=session.difficulty,
        )
        session.messages.append(res["response"])
        session.action_history.append(res)

        for tc in res.get("tool_calls", []):
            if tc["name"] == "conclude_session":
                session.is_concluded = True

        has_question = any(tc.get("name") == "ask_question" for tc in res.get("tool_calls", []))
        if not has_question and not session.is_concluded:
            from utils.llm import get_llm
            q_llm = get_llm()
            q_prompt = (
                f"You are conducting an active-recall revision session on: '{session.topic}' ({session.difficulty} level).\n"
                f"The student just answered: '{answer}'.\n"
                "Formulate the NEXT clear revision question to continue testing their understanding.\n"
                "Return ONLY the question text ending with a question mark. No preamble or numbering."
            )
            q_res = q_llm.invoke(q_prompt)
            q_text = getattr(q_res, "content", str(q_res)).strip().strip('"\'')
            res["tool_calls"].append({
                "name": "ask_question",
                "args": {"question": q_text, "difficulty": session.difficulty},
                "id": f"auto_q_{len(session.action_history)}"
            })

        return self._format_response(session, res)

    def conclude(self, session_id: str) -> dict:
        session = self.get(session_id)
        if not session:
            raise ValueError("Session not found")

        latest = session.action_history[-1] if session.action_history else None
        latest_tools = latest.get("tool_calls", []) if latest else []

        for tc in latest_tools:
            session.messages.append(
                ToolMessage(content="Action presented to student.", tool_call_id=tc["id"])
            )

        conclude_msg = HumanMessage(
            content=(
                "I would like to end the revision session now. "
                "Please evaluate my overall performance across all questions answered, "
                "and call conclude_session with my estimated mastery percentage (0-100%), "
                "a positive comprehensive summary, and specific weak topics I should review next time."
            )
        )
        session.messages.append(conclude_msg)

        res = step_tutor(
            session.messages,
            topic=session.topic,
            difficulty=session.difficulty,
        )
        session.messages.append(res["response"])
        session.action_history.append(res)
        session.is_concluded = True

        return self._format_response(session, res)

    def ask_doubt(self, session_id: str, question: str) -> dict:
        session = self.get(session_id)
        topic = session.topic if session else "General Topic"

        notes_text = ""
        if session:
            for act in session.action_history:
                for tc in act.get("tool_calls", []):
                    if tc.get("name") == "give_revision_notes":
                        notes_text += tc.get("args", {}).get("notes", "") + "\n"

        from utils.llm import get_llm
        from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

        system_msg = SystemMessage(
            content=(
                f"You are an encouraging, expert AI Tutor helping a student revise '{topic}'.\n"
                f"The student is asking questions or clarifying doubts about this topic.\n"
                f"Context Notes:\n{notes_text[:2500] if notes_text else 'No specific notes.'}\n\n"
                "Answer clearly, concisely, and helpfully. Use bullet points or code snippets when helpful."
            )
        )

        messages = [system_msg]
        if session:
            for item in session.doubt_history[-6:]:
                if item["role"] == "user":
                    messages.append(HumanMessage(content=item["content"]))
                else:
                    messages.append(AIMessage(content=item["content"]))

        messages.append(HumanMessage(content=question))

        llm = get_llm()
        response = llm.invoke(messages)
        content = getattr(response, "content", str(response))
        if isinstance(content, list):
            content = "".join([c.get("text", "") if isinstance(c, dict) else str(c) for c in content])

        answer = content.strip()

        if session:
            session.doubt_history.append({"role": "user", "content": question})
            session.doubt_history.append({"role": "assistant", "content": answer})

        return {"answer": answer}

    @staticmethod
    def _format_response(session: "Session", res: dict) -> dict:
        actions = []
        for tc in res.get("tool_calls", []):
            actions.append({"type": tc["name"], "args": tc["args"]})

        return {
            "session_id": session.id,
            "agent_text": res.get("content", "") or "",
            "actions": actions,
            "questions_answered": session.questions_answered,
            "is_concluded": session.is_concluded,
        }
