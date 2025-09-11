# agents/negotiation/negotiation_agent.py
import os
import google.generativeai as genai

class NegotiationAgent:
    def __init__(self, vendor_name: str, product: str, quantity: int):
        self.vendor_name = vendor_name
        self.product = product
        self.quantity = quantity

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in environment.")
        genai.configure(api_key=api_key)

        # Use a CURRENT model name
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        # or: genai.GenerativeModel("gemini-1.5-pro")

    def generate_email(self) -> str:
        prompt = f"""
        You are a procurement negotiator. Draft a concise, professional first outreach email
        to {self.vendor_name} about purchasing {self.quantity} units of "{self.product}".
        Ask for best price, delivery time, volume discount, and warranty/after-sales terms.
        Keep it 120–150 words, polite tone, subject line included.
        """
        try:
            resp = self.model.generate_content(prompt)
            return resp.text.strip()
        except Exception as e:
            # Fallback so the endpoint still returns something
            return (
                f"Subject: Request for Quote – {self.product}\n\n"
                f"Dear {self.vendor_name} Team,\n\n"
                f"We are interested in purchasing {self.quantity} units of {self.product}. "
                f"Could you share your best price, lead time, available volume discounts, and warranty terms?\n\n"
                f"Kind regards,\nProcureMate Procurement"
            )
