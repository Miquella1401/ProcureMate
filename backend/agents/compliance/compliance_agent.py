from crewai import Agent, LLM
from dotenv import load_dotenv
load_dotenv()

def create_compliance_agent():
    llm = LLM(model="gemini/gemini-2.5-pro", temperature=0.2, verbose=True)
    return Agent(
        role="Compliance Officer",
        goal="Check ranked vendor options against the provided procurement policy and output strict JSON.",
        backstory=(
            "An experienced procurement compliance specialist ensuring all vendors meet budget, "
            "delivery and certification rules. When data is missing, mark it as 'unknown' not failure."
        ),
        tools=[],
        llm=llm,
        verbose=True
    )
