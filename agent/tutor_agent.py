import re
import json
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from agent.tools import ALL_TOOLS, ask_question, give_revision_notes, explain_concept, test_code_execution, conclude_session
from utils.llm import get_llm

TUTOR_SYSTEM_PROMPT = """You are an elite, adaptive 1-on-1 AI Tutor conducting an interactive active-recall revision session with a student.

TOPIC: {topic}
TARGET DIFFICULTY: {difficulty}
{source_material_section}
YOUR GOAL:
Guide the student through mastering this topic using the following structured flow.

SESSION FLOW:
1. STARTING THE SESSION:
   - Call `give_revision_notes` ONLY. Provide comprehensive introductory revision notes covering the key concepts, definitions, examples, and common mistakes for the topic {doc_notes_rule}.
   - Do NOT ask a question yet. Wait for the student to say they are ready.

2. WHEN THE STUDENT SAYS THEY ARE READY FOR QUESTIONS:
   - Call `ask_question` to pose a clear baseline question to assess their understanding {doc_question_rule}.

3. CONTINUOUS Q&A (STRICT MANDATORY RULE):
   - In EVERY turn during Q&A, you MUST include a call to `ask_question`. Never stop asking questions!
   - IF THE STUDENT'S ANSWER WAS CORRECT:
     * Praise them in your text response and explain why their answer is right {doc_eval_rule}.
     * Then call `ask_question` with the next question (moving forward to new or deeper sub-topics from the material).
   - IF THE STUDENT'S ANSWER WAS INCORRECT:
     * In your text response, clearly state that their answer was WRONG and explain the correct answer {doc_eval_rule}.
     * Call `give_revision_notes` with concise notes on the specific concept they missed.
     * AND in the SAME turn, also call `ask_question` to ask another question so the quiz keeps going.

4. ENDING THE Q&A:
   - You must NEVER call `conclude_session` on your own. Keep asking questions turn after turn.
   - Only when the student explicitly requests to end or conclude the session, call `conclude_session` with mastery_percentage, summary, and weak_topics.

CRITICAL RULES:
- ALWAYS use tools.
- Keep tool argument text cleanly formatted and concise so JSON serializes properly.
- EVERY TURN AFTER AN ANSWER MUST HAVE AN `ask_question` TOOL CALL.
- If wrong: give notes AND ask the next question together in the same turn.
- The session must continue continuously until the student presses the End Q&A button.
{doc_strict_rules}
"""

def get_tutor_agent():
    llm = get_llm()
    return llm.bind_tools(ALL_TOOLS)


def recover_failed_tool_call(failed_gen_str: str) -> Optional[Dict[str, Any]]:
    """Rescue tool name and arguments from truncated or malformed JSON returned by Groq."""
    if not failed_gen_str:
        return None
    try:
        data = json.loads(failed_gen_str)
        if isinstance(data, dict) and "name" in data:
            args = data.get("arguments", {})
            if isinstance(args, str):
                args = json.loads(args)
            return {"name": data["name"], "args": args}
    except Exception:
        pass

    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', failed_gen_str)
    tool_name = name_match.group(1) if name_match else "give_revision_notes"

    if tool_name == "give_revision_notes":
        title_match = re.search(r'"topic_title"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', failed_gen_str)
        topic_title = title_match.group(1) if title_match else "Revision Notes"

        notes_match = re.search(r'"notes"\s*:\s*"(.*)', failed_gen_str, re.DOTALL)
        if notes_match:
            raw_notes = notes_match.group(1)
            raw_notes = re.sub(r'["}\s]+$', '', raw_notes)
            try:
                clean_notes = bytes(raw_notes, "utf-8").decode("unicode_escape")
            except Exception:
                clean_notes = raw_notes.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            return {
                "name": "give_revision_notes",
                "args": {"topic_title": topic_title, "notes": clean_notes}
            }

    elif tool_name == "ask_question":
        q_match = re.search(r'"question"\s*:\s*"(.*)', failed_gen_str, re.DOTALL)
        if q_match:
            raw_q = q_match.group(1)
            raw_q = re.sub(r'["}\s]+$', '', raw_q)
            try:
                clean_q = bytes(raw_q, "utf-8").decode("unicode_escape")
            except Exception:
                clean_q = raw_q.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')
            return {
                "name": "ask_question",
                "args": {"question": clean_q}
            }

    return None


def step_tutor(
    messages: List[Any],
    topic: str,
    difficulty: str = "Beginner",
    doc_text: Optional[str] = None
) -> Dict[str, Any]:
    agent = get_tutor_agent()

    if doc_text and doc_text.strip():
        trimmed_doc = doc_text.strip()[:25000]
        source_material_section = (
            "\nSOURCE MATERIAL / UPLOADED DOCUMENT CONTENT:\n"
            "==================================================\n"
            f"{trimmed_doc}\n"
            "==================================================\n"
        )
        doc_notes_rule = "(based DIRECTLY on the uploaded source material above)"
        doc_question_rule = "(derived directly from the uploaded source material)"
        doc_eval_rule = "based strictly on the uploaded source material"
        doc_strict_rules = (
            "- MANDATORY GROUNDING: The student uploaded the source material above. "
            "You MUST base ALL revision notes, questions, evaluations, correct answers, and explanations strictly on this uploaded document. "
            "Do NOT invent or pull outside topics, facts, or definitions from general internet knowledge that are not in this document. "
            "Evaluate student answers strictly against what is written in their document."
        )
    else:
        source_material_section = ""
        doc_notes_rule = ""
        doc_question_rule = ""
        doc_eval_rule = ""
        doc_strict_rules = ""

    sys_prompt_text = TUTOR_SYSTEM_PROMPT.format(
        topic=topic,
        difficulty=difficulty,
        source_material_section=source_material_section,
        doc_notes_rule=doc_notes_rule,
        doc_question_rule=doc_question_rule,
        doc_eval_rule=doc_eval_rule,
        doc_strict_rules=doc_strict_rules,
    )

    sys_msg = SystemMessage(content=sys_prompt_text)
    full_messages = [sys_msg] + messages

    try:
        response = agent.invoke(full_messages)
        tool_calls = getattr(response, "tool_calls", [])
    except Exception as e:
        err_str = str(e)
        recovered_call = None

        failed_gen = None
        if hasattr(e, "body") and isinstance(e.body, dict):
            err_dict = e.body.get("error", {})
            if isinstance(err_dict, dict):
                failed_gen = err_dict.get("failed_generation")

        if not failed_gen and "failed_generation" in err_str:
            m = re.search(r"['\"]failed_generation['\"]\s*:\s*['\"](.*)", err_str)
            if m:
                failed_gen = m.group(1)

        if failed_gen:
            recovered_call = recover_failed_tool_call(str(failed_gen))

        if recovered_call:
            recovered_call["id"] = "recovered_tool_call"
            tool_calls = [recovered_call]
            response = AIMessage(content="", tool_calls=tool_calls)
        else:
            # Fallback: invoke LLM directly without tool binding
            plain_llm = get_llm()
            plain_res = plain_llm.invoke(full_messages)
            text_out = getattr(plain_res, "content", str(plain_res)).strip()

            is_start = any(
                "give_revision_notes" in getattr(m, "content", "")
                for m in messages
                if isinstance(m, HumanMessage)
            )
            if is_start:
                tool_calls = [{
                    "name": "give_revision_notes",
                    "args": {
                        "topic_title": f"{topic} Revision Notes",
                        "notes": text_out,
                        "key_points": ""
                    },
                    "id": "plain_fallback_notes"
                }]
            else:
                tool_calls = [{
                    "name": "ask_question",
                    "args": {"question": text_out},
                    "id": "plain_fallback_question"
                }]
            response = AIMessage(content="", tool_calls=tool_calls)

    if not tool_calls and response.content:
        tool_calls = [{
            "name": "ask_question",
            "args": {"question": response.content},
            "id": "fallback_call"
        }]

    return {
        "response": response,
        "tool_calls": tool_calls,
        "content": response.content
    }
