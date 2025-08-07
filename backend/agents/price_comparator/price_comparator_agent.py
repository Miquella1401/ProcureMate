from crewai import Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os

load_dotenv()

def create_price_comparator_agent():
    llm = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-pro",  
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        verbose=True
    )

    return Agent(
        role='Price Comparator Agent',
        goal='Compare vendors based on price, delivery time, and product specifications. Provide a ranked list of best options.',
        backstory=(
            "You are a procurement price analyst. Your role is to evaluate multiple vendor offers and rank them based on overall value. "
            "You factor in unit price, delivery time, and alignment with product requirements."
        ),
        tools=[],
        llm=llm,
        verbose=True
    )
