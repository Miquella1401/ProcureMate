# agents/price_comparator_agent.py
"""
LLM-free Price Comparator.

We keep a function-based API so the pipeline can call it directly without using CrewAI/LLM.
"""

from __future__ import annotations
from typing import Any, Dict, List
from tools.ranking import simple_rank_offers

def create_price_comparator_agent():
    """
    Legacy compatibility stub. We no longer return a CrewAI Agent here, because
    we don't want *any* LLM calls for price comparison.

    If your pipeline tries to *use* the Agent, redirect it to call
    `run_price_comparison_offline(offers, query)` instead.
    """
    return None  # Not used anymore

def run_price_comparison_offline(offers: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
    """
    New entrypoint the pipeline should call directly.
    """
    return simple_rank_offers(offers, query or "")
