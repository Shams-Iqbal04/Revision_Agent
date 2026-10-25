from langgraph.graph import StateGraph, START, END

from agent.state import RevisionState
from agent.prompts import (
    NOTES_PROMPT,
    QUESTIONS_PROMPT,
    FLASHCARD_PROMPT,
    EVALUATION_PROMPT
)

from utils.llm import get_llm

llm = get_llm()


def extract_text(response) -> str:
    if hasattr(response, "content"):
        return str(response.content).strip()
    return str(response).strip()


def generate_notes(state: RevisionState):
    prompt = NOTES_PROMPT.format(
        topic=state["topic"],
        difficulty=state["difficulty"]
    )
    response = llm.invoke(prompt)
    return {
        "notes": extract_text(response)
    }


def generate_questions(state: RevisionState):
    prompt = QUESTIONS_PROMPT.format(
        topic=state["topic"],
        difficulty=state["difficulty"]
    )
    response = llm.invoke(prompt)
    text = extract_text(response)

    import re
    raw_lines = text.split("\n")
    questions_list = []
    for line in raw_lines:
        cleaned = re.sub(r"^(?:\d+[\.\)]|Question\s*\d+[\:\.]?|[\-\*])\s*", "", line.strip()).strip()
        cleaned = cleaned.replace("**", "")
        if cleaned and len(cleaned) > 3:
            questions_list.append({"question": cleaned})

    if not questions_list and text:
        questions_list = [{"question": text}]

    return {
        "questions": questions_list
    }


def generate_flashcards(state: RevisionState):
    prompt = FLASHCARD_PROMPT.format(
        topic=state["topic"]
    )

    response = llm.invoke(prompt)
    text = extract_text(response)
    text = text.replace("\r\n", "\n")

    import re
    flashcards = []

    pattern = re.compile(
        r"(?:Card\s*\d+[\:\.\s]*)?"
        r"(?:\#+\s*)?"
        r"(?:\*\*)?Question(?:\s*\d+)?(?:\*\*)?[\:\.\s]+(.*?)"
        r"(?:\*\*)?Answer(?:\s*\d+)?(?:\*\*)?[\:\.\s]+(.*?)"
        r"(?=(?:Card\s*\d+|\#+\s*Card|\bQuestion\b|\Z))",
        re.IGNORECASE | re.DOTALL
    )

    matches = pattern.findall(text)
    for q, a in matches:
        q_clean = q.strip().strip("*_#` \n")
        a_clean = a.strip().strip("*_#` \n")
        a_clean = re.split(r"\n\s*(?:Card|\#+)\s*\d+", a_clean, flags=re.IGNORECASE)[0].strip()
        if q_clean and a_clean:
            flashcards.append({
                "question": q_clean,
                "answer": a_clean
            })

    if not flashcards and text:
        parts = re.split(r"(?i)(?=Card\s*\d+)", text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lines = [l.strip() for l in part.split("\n") if l.strip()]
            q_str, a_str = "", ""
            for l in lines:
                if re.match(r"(?i)^(?:\*\*)?Question", l):
                    q_str = re.sub(r"(?i)^(?:\*\*)?Question(?:\s*\d+)?(?:\*\*)?[\:\.\s]*", "", l).strip()
                elif re.match(r"(?i)^(?:\*\*)?Answer", l):
                    a_str = re.sub(r"(?i)^(?:\*\*)?Answer(?:\s*\d+)?(?:\*\*)?[\:\.\s]*", "", l).strip()
            if q_str and a_str:
                flashcards.append({"question": q_str, "answer": a_str})

    if not flashcards and text:
        flashcards.append({
            "question": "Key Concepts to Revise",
            "answer": text
        })

    return {
        "flashcards": flashcards
    }


def evaluate_revision(state: RevisionState):
    prompt = EVALUATION_PROMPT.format(
        topic=state["topic"],
        questions=state["questions"],
        answers=state["user_answers"]
    )
    response = llm.invoke(prompt)
    return {
        "feedback": extract_text(response)
    }


def build_graph():
    graph = StateGraph(RevisionState)

    graph.add_node("generate_notes", generate_notes)
    graph.add_node("generate_questions", generate_questions)
    graph.add_node("generate_flashcards", generate_flashcards)
    graph.add_node("evaluate_revision", evaluate_revision)

    graph.add_edge(START, "generate_notes")
    graph.add_edge("generate_notes", "generate_questions")
    graph.add_edge("generate_notes", "generate_flashcards")
    graph.add_edge("generate_questions", END)
    graph.add_edge("generate_flashcards", END)

    return graph.compile()


revision_agent = build_graph()


def ask_tutor(topic: str, notes: str, user_query: str) -> str:
    from agent.prompts import TUTOR_CHAT_PROMPT
    prompt = TUTOR_CHAT_PROMPT.format(
        topic=topic,
        notes=notes,
        user_query=user_query
    )
    response = llm.invoke(prompt)
    return extract_text(response)
