from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

def create_requirement_agent():
  
    llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-pro",  
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    verbose=True,
    stream=False
)



    return Agent(
        role="Procurement Requirement Analyst",
        goal="Extract structured requirements from unstructured procurement requests.",
        backstory="You help define clear product requirements from vague business needs.",
        tools=[],
        llm=llm,
        verbose=True
    )
