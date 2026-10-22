import io
import sys
from langchain_core.tools import tool

@tool
def ask_question(question: str, difficulty: str = "Medium", hint: str = "") -> str:
    """Ask the student a targeted revision question to assess their understanding.
    Args:
        question: The clear, concise question to ask.
        difficulty: 'Easy', 'Medium', or 'Hard'.
        hint: An optional helpful hint if the student gets stuck.
    """
    return f"Question posed: {question}"

@tool
def give_revision_notes(topic_title: str, notes: str, key_points: str = "") -> str:
    """Provide focused revision notes on a specific sub-topic when the student answered incorrectly or needs reinforcement.
    Use this when:
    - The student gave a wrong answer — provide notes covering the specific concept they got wrong.
    - The student seems confused — provide notes to clarify the concept.
    - At the start of a session — provide introductory revision notes on the main topic.
    Args:
        topic_title: The specific sub-topic or concept name these notes cover.
        notes: Detailed revision notes in markdown format. Include definitions, key concepts, examples, and common mistakes.
        key_points: Bullet-point summary of the most important takeaways (use newlines between points).
    """
    return f"Revision notes provided for: {topic_title}"

@tool
def explain_concept(concept_title: str, explanation: str, code_example: str = "") -> str:
    """Explain a concept in simple, intuitive terms when the student is confused or makes a mistake.
    Args:
        concept_title: Name of the concept.
        explanation: Clear explanation addressing the misconception.
        code_example: Optional Python code example demonstrating the concept.
    """
    return f"Explained: {concept_title}"

@tool
def test_code_execution(code: str) -> str:
    """Safely execute a Python snippet in a sandbox to verify code output or test student code.
    Args:
        code: Python code to execute.
    """
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output
    try:
        # Limited execution environment
        exec_globals = {"__builtins__": __builtins__}
        exec(code, exec_globals)
        output = redirected_output.getvalue()
        return output if output else "Code executed successfully with no output."
    except Exception as e:
        return f"Execution Error: {e}"
    finally:
        sys.stdout = old_stdout

@tool
def conclude_session(mastery_percentage: int, summary: str, weak_topics: list = None) -> str:
    """Conclude the revision session when the student has demonstrated sufficient understanding.
    Args:
        mastery_percentage: Estimated student mastery (0-100%).
        summary: Positive summary of progress made.
        weak_topics: List of topics recommended for future review.
    """
    return f"Session concluded with {mastery_percentage}% mastery."

ALL_TOOLS = [
    ask_question,
    give_revision_notes,
    explain_concept,
    test_code_execution,
    conclude_session
]
