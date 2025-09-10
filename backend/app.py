# app.py
from flask import Flask, request, jsonify
from connect_agents import run_procurement_pipeline

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"message": "ProcureMate Flask backend is running!"})

@app.route("/api/run", methods=["POST"])
def run_pipeline():
    data = request.get_json(force=True) or {}
    request_text = data.get("request_text", "")
    policy_text  = data.get("policy_text", "")
    buyer_info   = data.get("buyer_info")  # optional

    result = run_procurement_pipeline(
        request_text=request_text,
        policy_text=policy_text,
        buyer_info=buyer_info
    )
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
