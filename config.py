import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # OpenAI settings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_API_BASE = os.getenv('OPENAI_API_BASE')
    OPENAI_API_VERSION = os.getenv('API_VERSION')
    OPENAI_ORG = os.getenv('OPENAI_ORGANIZATION')
    OPENAI_MODEL = os.getenv('MODEL')

    # Agentic loop settings
    MAX_ITERATIONS = 15
    MAX_MESSAGES = 20
    MAX_RESULT_LENGTH = 2000
