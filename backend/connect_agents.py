# connect_agents.py
from crewai import Crew, Task
from agents.requirement.requirement_agent import create_requirement_agent
from agents.market_intelligence.market_intelligence_agent import create_market_intelligence_agent
from agents.price_comparator.price_comparator_agent import create_price_comparator_agent
from agents.compliance.compliance_agent import create_compliance_agent
from agents.po_generator.po_generator_agent import create_po_generator_agent

import json
import re
from typing import Any, Optional


def _extract_json_block(text: str) -> Optional[Any]:
    """
    Pull the last JSON object/array from a string.
    1) Prefer a fenced ```json ... ``` block (most reliable).
    2) Else fallback to the last {...} or [...] in the text.
    Returns a Python object (dict/list) or None.
    """
    if not text:
        return None

    # 1) Try fenced JSON block(s)
    fenced = re.findall(r"```json\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced:
        candidate = fenced[-1].strip()
        try:
            return json.loads(candidate)
        except Exception:
            pass  # fall through

    # 2) Fallback: last {...} or [...]
    #    Naive but effective given our task prompts are strict JSON.
    matches = list(re.finditer(r"\{[\s\S]*\}|\[[\s\S]*\]", text))
    if matches:
        last = matches[-1].group(0)
        try:
            return json.loads(last)
        except Exception:
            return None

    return None


def run_procurement_pipeline(
    request_text: str,
    policy_text: str = (
        "Policy:\n"
        "- Budget per unit <= $500\n"
        "- Delivery <= 14 days\n"
        "- Prefer ISO-9001 certified vendors\n"
        "- Region: EU-friendly shipping\n"
    ),
    buyer_info: dict | None = None
):
    if buyer_info is None:
        buyer_info = {
            "buyer_name": "ProcureMate GmbH",
            "buyer_email": "ops@procuremate.ai",
            "buyer_address": "Hauptstr. 1, 69117 Heidelberg, Germany"
        }

    # === Agents ===
    requirement_agent = create_requirement_agent()
    market_agent      = create_market_intelligence_agent()  # exposes fetch_vendor_offers tool
    price_agent       = create_price_comparator_agent()
    compliance_agent  = create_compliance_agent()
    po_agent          = create_po_generator_agent()

    # === Task 1: Requirement Extraction ===
    task1 = Task(
        description=(
            "Extract structured product details from the following request:\n"
            f"'{request_text}'\n\n"
            "Return a compact JSON object ONLY with keys: "
            "product_type (string), quantity (int), deadline (string - month name or YYYY-MM-DD)."
        ),
        expected_output='{"product_type":"ergonomic chair","quantity":50,"deadline":"September"}',
        agent=requirement_agent
    )

    # === Task 2: Market Intelligence (call fetch_vendor_offers tool) ===
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

    # === Task 3: Price Comparator (ranking JSON) ===
    task3 = Task(
        description=(
            "Parse the JSON array from Task 2. Rank the vendors by overall value using:\n"
            "- Price (lower is better) weight=0.6 (treat null as unknown; do not penalize heavily),\n"
            "- Availability text hint (e.g., 'in stock' > 'backorder') weight=0.2,\n"
            "- Title relevance to the required product weight=0.2.\n"
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

    # === Task 4: Compliance Check ===
    task4 = Task(
        description=(
            "Evaluate the ranked vendors from Task 3 against the following policy:\n"
            f"{policy_text}\n\n"
            "Instructions:\n"
            "1) Parse Task 3 JSON to read 'ranking'.\n"
            "2) For each vendor, assess compliance with the policy. If any policy criteria cannot be "
            "   verified from available data, mark that criterion as 'unknown' and do not fail the vendor solely for 'unknown'.\n"
            "3) Return ONLY a JSON object with keys:\n"
            "   {\n"
            "     \"compliance_report\": [\n"
            "        {\"vendor_name\":\"...\",\"url\":\"...\",\"price\":499.0,\"currency\":\"USD\",\n"
            "         \"availability\":\"In stock\",\"score\":88,\n"
            "         \"compliant\": true/false,\n"
            "         \"issues\": [\"Budget exceeded\", \"Delivery unknown\", \"ISO-9001 unknown\"],\n"
            "         \"reason\": \"Short justification\"\n"
            "        }, ...\n"
            "     ],\n"
            "     \"best_candidates\": [\"Vendor A\", \"Vendor B\"],\n"
            "     \"notes\": \"Any caveats or missing information.\"\n"
            "   }\n"
        ),
        expected_output=(
            "{"
            "\"compliance_report\":["
            "{\"vendor_name\":\"...\",\"url\":\"...\",\"price\":499.0,\"currency\":\"USD\",\"availability\":\"In stock\","
            "\"score\":88,\"compliant\":true,\"issues\":[],\"reason\":\"Within budget; availability confirmed\"}"
            "],"
            "\"best_candidates\":[\"...\"],"
            "\"notes\":\"...\""
            "}"
        ),
        agent=compliance_agent,
        context=[task1, task2, task3]
    )

    # === Task 5: PO Generator ===
    task5 = Task(
        description=(
            "Create a Purchase Order (PO) using the requirement from Task 1 and the best candidate(s) "
            "from Task 4's compliance output.\n\n"
            "Buyer Info (use this in the PO header):\n"
            f"{buyer_info}\n\n"
            "PO Requirements:\n"
            "- Choose the top compliant vendor from Task 4; if none are compliant, choose the highest-scoring vendor.\n"
            "- Quantity from Task 1; compute line total = quantity * unit price (if price unknown, set null and note it).\n"
            "- Include basic delivery terms if known; otherwise mark as 'unknown'.\n"
            "- Include a concise 'notes' field with any caveats.\n\n"
            "Return ONLY a JSON object with keys:\n"
            "{\n"
            "  \"po_number\": \"string\",\n"
            "  \"date\": \"YYYY-MM-DD\",\n"
            "  \"buyer\": {\"name\":\"...\",\"email\":\"...\",\"address\":\"...\"},\n"
            "  \"vendor\": {\"name\":\"...\",\"url\":\"...\"},\n"
            "  \"items\": [ {\"description\":\"<product_type>\", \"quantity\":<int>, \"unit_price\":<number|null>, \"currency\":\"...\", \"line_total\":<number|null>} ],\n"
            "  \"totals\": {\"subtotal\":<number|null>, \"currency\":\"...\"},\n"
            "  \"delivery_terms\": \"string or 'unknown'\",\n"
            "  \"notes\": \"string\"\n"
            "}\n"
        ),
        expected_output=(
            "{"
            "\"po_number\":\"PO-2025-0001\",\"date\":\"2025-09-10\","
            "\"buyer\":{\"name\":\"ProcureMate GmbH\",\"email\":\"ops@procuremate.ai\",\"address\":\"Hauptstr. 1, 69117 Heidelberg, Germany\"},"
            "\"vendor\":{\"name\":\"...\",\"url\":\"...\"},"
            "\"items\":[{\"description\":\"ergonomic chair\",\"quantity\":50,\"unit_price\":499.0,\"currency\":\"USD\",\"line_total\":24950.0}],"
            "\"totals\":{\"subtotal\":24950.0,\"currency\":\"USD\"},"
            "\"delivery_terms\":\"unknown\",\"notes\":\"Price confirmed; delivery unknown\""
            "}"
        ),
        agent=po_agent,
        context=[task1, task3, task4]
    )

    # === Crew ===
    crew = Crew(
        agents=[requirement_agent, market_agent, price_agent, compliance_agent, po_agent],
        tasks=[task1, task2, task3, task4, task5],
        verbose=True,
    )

    # Run and normalize into JSON-serializable payload
    result = crew.kickoff()

    # CrewOutput -> try .raw or .output, else str()
    final_text = getattr(result, "raw", None) or getattr(result, "output", None) or str(result)

    parsed = _extract_json_block(final_text)

    return {
        "ok": True,
        "final": parsed if parsed is not None else final_text,  # dict/list if parsed; raw string fallback
    }
