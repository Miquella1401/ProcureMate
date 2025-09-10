from crewai import Agent, LLM
import os
from dotenv import load_dotenv
load_dotenv()

# Choose a model with higher RPM for Task 5
# Option 1 (recommended): OpenAI
#   - set OPENAI_API_KEY in your environment
#   - default to gpt-4o-mini which is fast+cheap
# Option 2: Fast Gemini model (if you don't want OpenAI)
#   - set LLM_MODEL_TASK5="gemini/gemini-1.5-flash"
MODEL = os.getenv("LLM_MODEL_TASK5", "openai/gpt-4o-mini")

def create_po_generator_agent():
    llm = LLM(
        model=MODEL,
        temperature=0.1,
        verbose=True,
        # litellm kwargs
        max_retries=3,              # auto-retry on 429
        request_timeout=90,         # seconds
    )
    return Agent(
        role="Purchase Order Generator",
        goal="Generate a clean Purchase Order JSON from requirement + compliance results.",
        backstory="A meticulous assistant drafting formal purchase orders from selected vendors.",
        tools=[],   # later we can add a PDF/MD writer tool
        llm=llm,
        verbose=True
    )
