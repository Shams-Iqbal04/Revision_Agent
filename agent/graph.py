from langgraph.graph import StateGraph, START, END

from agent.state import RevisionState
from agent.prompts import (
    NOTES_PROMPT,
    QUESTION_PROMPT,
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
        difficulty=state["difficulty"],
        source_material_section=""
    )
    response = llm.invoke(prompt)
    return {
        "notes": extract_text(response)
    }


def generate_questions(state: RevisionState):
    prompt = QUESTION_PROMPT.format(
        topic=state["topic"],
        difficulty=state["difficulty"],
        source_material_section="",
        previous_context=""
    )
    response = llm.invoke(prompt)
    text = extract_text(response)

    return {
        "questions": [{"question": text}]
    }


def evaluate_revision(state: RevisionState):
    prompt = EVALUATION_PROMPT.format(
        topic=state["topic"],
        question=state.get("questions", [{}])[0].get("question", ""),
        student_answer=state.get("user_answers", [""])[-1] if state.get("user_answers") else "",
        source_material_section=""
    )
    response = llm.invoke(prompt)
    return {
        "feedback": extract_text(response)
    }


def build_graph():
    graph = StateGraph(RevisionState)

    graph.add_node("generate_notes", generate_notes)
    graph.add_node("generate_questions", generate_questions)
    graph.add_node("evaluate_revision", evaluate_revision)

    graph.add_edge(START, "generate_notes")
    graph.add_edge("generate_notes", "generate_questions")
    graph.add_edge("generate_questions", END)

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
