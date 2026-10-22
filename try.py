import sys
sys.stdout.reconfigure(encoding='utf-8')
from agent.graph import revision_agent


state = {
    "topic": "Python Garbage Collection",
    "difficulty": "Beginner",
    "notes": "",
    "questions": [],
    "flashcards": [],
    "user_answers": [],
    "score": 0,
    "feedback": "",
    "next_revision": ""
}


result = revision_agent.invoke(state)


print("\n================ NOTES ================\n")

print(result["notes"])


print("\n================ QUESTIONS ================\n")

for i, q in enumerate(result["questions"], 1):
    print(f"{i}. {q['question']}")
    print()


print("\n================ FLASHCARDS ================\n")

for i, card in enumerate(result["flashcards"], 1):
    print(f"Flashcard {i}")
    print(f"Question: {card['question']}")
    print(f"Answer: {card['answer']}")
    print()