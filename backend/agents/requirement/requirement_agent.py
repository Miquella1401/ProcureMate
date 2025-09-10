from crewai import Agent, LLM
from dotenv import load_dotenv
import os

load_dotenv()

def create_requirement_agent():
    # Use CrewAI's built-in LLM wrapper
    llm = LLM(
        model="gemini/gemini-2.5-pro",   # ✅ note the "gemini/" prefix
        temperature=0.2,
        verbose=True
    )

    return Agent(
        role="Procurement Requirement Analyst",
        goal="Extract structured requirements from unstructured procurement requests.",
        backstory="You help define clear product requirements from vague business needs.",
        tools=[],
        llm=llm,
        verbose=True
    )
