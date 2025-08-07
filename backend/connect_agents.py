
from crewai import Crew, Task


from agents.requirement.requirement_agent import create_requirement_agent
from agents.market_intelligence.market_intelligence_agent import create_market_intelligence_agent

def initialize_agents():
  
    requirement_agent = create_requirement_agent()
    market_agent = create_market_intelligence_agent()

    # Define tasks
    task1 = Task(
        description="Extract structured product details from: 'We need 50 ergonomic chairs for our new office setup by September.'",
        expected_output="Structured product information including product type, quantity, and deadline.",
        agent=requirement_agent
    )

    task2 = Task(
        description="Based on the structured requirement from Task 1, suggest 3 suitable vendors with product details.",
        expected_output="A list of 3 vendors with product name, pricing, and delivery time.",
        agent=market_agent,
        context=[task1]
    )

    # code for Build the Crew
    crew = Crew(
        agents=[requirement_agent, market_agent],
        tasks=[task1, task2],
        verbose=2
    )

    # code for Running the Crew and return result
    result = crew.kickoff()
    print("\n=== Final Result ===\n")
    print(result)
    return result
