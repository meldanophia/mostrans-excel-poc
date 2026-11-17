"""Standalone Flask POC, never connect this endpoint to production DB.
Run with `python flask_poc_api.py` locally; deploy behind HTTPS for Excel Online.
"""
import os
from flask import Flask, jsonify, request

app = Flask(__name__)
ALLOWED_ORIGIN = "https://meldanophia.github.io"

@app.after_request
def add_cors(response):
    if request.headers.get("Origin") == ALLOWED_ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
        response.headers["Vary"] = "Origin"
        response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Cache-Control"] = "no-store"
    return response

@app.route("/poc/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS": return "", 204
    return jsonify(status="ok", service="mostrans-flask-poc", database_used=False)

@app.route("/poc/echo", methods=["POST", "OPTIONS"])
def echo():
    if request.method == "OPTIONS": return "", 204
    if request.content_length is None or request.content_length > 100_000:
        return jsonify(error="Payload too large or length missing"), 413
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("operation") != "POC_ONLY_NO_SQL":
        return jsonify(error="Invalid POC operation"), 400
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) != 3:
        return jsonify(error="Expected exactly 3 dummy rows"), 400
    if [r.get("row_id") for r in rows if isinstance(r, dict)] != ["dummy-001","dummy-002","dummy-003"]:
        return jsonify(error="Only synthetic test rows allowed"), 400
    return jsonify(status="ok", received_rows=len(rows), database_used=False,
                   results=[{"row_id":r["row_id"],"status":"received"} for r in rows])

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "6077")), debug=False)
