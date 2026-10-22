NOTES_PROMPT = """
Generate concise revision notes about {topic}.

Difficulty: {difficulty}

Include:
1. Important concepts
2. Definitions
3. Key points
4. Examples
5. Common mistakes

Return ONLY the notes.
Do not repeat the prompt.
Do not say "Sure".
Do not explain what you are doing.
"""


QUESTIONS_PROMPT = """
Generate exactly 5 revision questions about {topic}.

Difficulty: {difficulty}

Rules:
- Generate exactly 5 questions.
- Each question must be on a separate line.
- Each question must end with a question mark.
- Do not provide answers.
- Do not provide explanations.
- Do not repeat the prompt.

Output ONLY the 5 questions.
"""


FLASHCARD_PROMPT = """
Create exactly 10 flashcards for the topic: {topic}

Use this EXACT format for every card:

Card 1
Question: <Write concise question here>
Answer: <Write concise answer here>

Card 2
Question: <Write concise question here>
Answer: <Write concise answer here>

Continue until Card 10.

Rules:
- Do not use markdown headers (like # or ####) or markdown bolding (like **) for Question or Answer labels.
- Use plain text "Card 1", "Question:", "Answer:".
- Keep questions concise and clear.
- Keep answers informative yet concise.
- Do not add any preamble, intro, or concluding text. Output only the cards.
"""


EVALUATION_PROMPT = """
Evaluate the student's answers.

Topic:
{topic}

Questions:
{questions}

Student answers:
{answers}

Give:

1. Score out of 10
2. Correct concepts
3. Incorrect concepts
4. Topics that need revision
5. Suggestions for next revision
"""


TUTOR_CHAT_PROMPT = """
You are an expert AI Tutor helping a student revise the topic: {topic}.

Student Question:
{user_query}

Context Notes:
{notes}

Provide a helpful, clear, and encouraging explanation. Use concise formatting or code examples if helpful.
"""