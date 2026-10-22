
from typing import TypedDict, List, Dict


class RevisionState(TypedDict):

    topic: str

    difficulty: str

    notes: str

    questions: List[Dict]

    flashcards: List[Dict]

    user_answers: List[str]

    score: int

    feedback: str

    next_revision: str
