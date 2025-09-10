from crewai import Agent, LLM
from crewai.tools import tool
from dotenv import load_dotenv
import os, json
from tools.scraper_tools import fetch_vendor_offers

load_dotenv()

@tool("fetch_vendor_offers")
def fetch_vendor_offers_tool(query: str) -> str:
    """
    Fetch live vendor offers for a product query.
    Returns a JSON string list of {vendor_name, url, title, price, currency, availability, ...}
    """
    offers = fetch_vendor_offers(query, max_vendors=3)
    return json.dumps(offers, ensure_ascii=False)

def create_market_intelligence_agent():
    llm = LLM(model="gemini/gemini-2.5-pro", temperature=0.2, verbose=True)
    return Agent(
        role="Market Intelligence Agent",
        goal="Use the fetch_vendor_offers tool to get live prices/availability and return normalized offers.",
        backstory="You gather up-to-date vendor data via scraping.",
        tools=[fetch_vendor_offers_tool],
        llm=llm,
        verbose=True,
    )
