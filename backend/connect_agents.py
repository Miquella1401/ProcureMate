from crewai import Crew, Task

from agents.requirement.requirement_agent import create_requirement_agent
from agents.market_intelligence.market_intelligence_agent import create_market_intelligence_agent
from agents.price_comparator.price_comparator_agent import create_price_comparator_agent

def initialize_agents():
    requirement_agent = create_requirement_agent()
    market_agent = create_market_intelligence_agent()   # <-- must include fetch_vendor_offers tool
    price_agent = create_price_comparator_agent()

    # Task 1: same as before
    task1 = Task(
        description=(
            "Extract structured product details from the following request:\n"
            "'We need 50 ergonomic chairs for our new office setup by September.'\n\n"
            "Return a compact JSON object ONLY with keys: "
            "product_type (string), quantity (int), deadline (string - month name or YYYY-MM-DD)."
        ),
        expected_output='{"product_type":"ergonomic chair","quantity":50,"deadline":"September"}',
        agent=requirement_agent
    )

    # Task 2: tell the agent to CALL THE TOOL for real-time prices and return ONLY JSON
    task2 = Task(
        description=(
            "Using the structured requirement from Task 1, get live vendor offers.\n"
            "- Derive a concise search phrase from product_type (e.g., 'ergonomic chair').\n"
            "- CALL THE TOOL fetch_vendor_offers with that phrase to scrape live data.\n"
            "- Return ONLY a JSON array (no markdown, no prose). Each element must have:\n"
            "  vendor_key, vendor_name, url, title, price (number or null), currency (string or null), "
            "availability (string or null), timestamp (int).\n"
            "If a site lacks price, set price to null and still include the record."
        ),
        expected_output=(
            '[{"vendor_key":"autonomous_ergochair_pro","vendor_name":"Autonomous ErgoChair Pro",'
            '"url":"...","title":"...","price":499.0,"currency":"USD","availability":"In stock","timestamp":1725950000}]'
        ),
        agent=market_agent,
        context=[task1]
    )

    # Task 3: read that JSON and rank vendors (still with the LLM), output a clean result
    task3 = Task(
        description=(
            "Parse the JSON array from Task 2. Rank the vendors by overall value using:\n"
            "- Price (lower is better) weight=0.6 (treat null as unknown; do not penalize heavily),\n"
            "- Availability text hint (e.g., 'in stock' > 'backorder') weight=0.2,\n"
            "- Title relevance to 'ergonomic chair' weight=0.2.\n"
            "Return ONLY a JSON object with keys:\n"
            "  'ranking': [ {vendor_name, url, price, currency, availability, score (0-100), reason} ... ],\n"
            "  'notes': 'any caveats about missing prices or parsing'."
        ),
        expected_output=(
            '{"ranking":[{"vendor_name":"...","url":"...","price":499.0,"currency":"USD",'
            '"availability":"In stock","score":88,"reason":"Lowest price, in stock"}],"notes":"..."}'
        ),
        agent=price_agent,
        context=[task1, task2]
    )

    crew = Crew(
        agents=[requirement_agent, market_agent, price_agent],
        tasks=[task1, task2, task3],
        verbose=True,
    )

    result = crew.kickoff()
    print("\n=== Final Result ===\n")
    print(result)
    return result
