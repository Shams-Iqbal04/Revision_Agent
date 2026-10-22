import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

def get_llm():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in environment or .env file.")
    
    # Strip any accidental whitespace or quotes
    api_key = api_key.strip().strip('"\'')
    
    # Selected best model: openai/gpt-oss-120b (120B parameter state-of-the-art model on Groq)
    # Fast, highly accurate, and excels at instruction following and educational formatting
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    return ChatGroq(
        model=model,
        temperature=0.2,
        groq_api_key=api_key,
        max_tokens=1500
    )