from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os


load_dotenv()

def create_market_intelligence_agent():
  
    llm = ChatGoogleGenerativeAI(
    model="models/gemini-2.5-pro",  
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    verbose=True,
    stream=False
)



    return Agent(
        role="Market Intelligence Agent",
        goal="Provide vendor options based on given product requirements.",
        backstory="You search vendor databases or catalogs and suggest suitable options.",
        tools=[],
        llm=llm,
        verbose=True
    )
