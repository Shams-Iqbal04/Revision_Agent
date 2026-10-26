import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq

ROOT_DIR = Path(__file__).resolve().parent.parent
env_path = ROOT_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


def get_llm(max_tokens: int = 4096):
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set in environment or .env file."
        )

    api_key = api_key.strip().strip('"\'')
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

    return ChatGroq(
        model=model,
        temperature=0.2,
        groq_api_key=api_key,
        max_tokens=max_tokens
    )
