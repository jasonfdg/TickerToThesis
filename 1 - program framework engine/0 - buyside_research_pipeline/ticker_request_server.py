#!/usr/bin/env python3
"""
Ticker Request Server

A simple Flask server that receives ticker requests from Ghost members
and tracks them in a local JSON file with counts.

Usage:
    python ticker_request_server.py [--port PORT]

The server exposes:
    POST /api/ticker-request - Submit a ticker request
    GET /api/ticker-requests - View all requests (for admin)
"""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for Ghost frontend

# File to store ticker request counts
DATA_DIR = Path(__file__).parent.parent.parent / "2 - report output"
REQUESTS_FILE = DATA_DIR / "ticker_requests.json"


def load_requests() -> dict:
    """Load ticker requests from file."""
    if REQUESTS_FILE.exists():
        with open(REQUESTS_FILE, "r") as f:
            return json.load(f)
    return {"requests": {}, "history": []}


def save_requests(data: dict) -> None:
    """Save ticker requests to file."""
    REQUESTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REQUESTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/api/ticker-request", methods=["POST"])
def submit_ticker_request():
    """
    Submit a ticker request.

    Expected JSON body:
        {"ticker": "AAPL"}

    Returns:
        {"success": true, "ticker": "AAPL", "count": 3}
    """
    try:
        body = request.get_json()
        if not body or "ticker" not in body:
            return jsonify({"success": False, "error": "Missing ticker"}), 400

        # Normalize ticker (uppercase, strip whitespace)
        ticker = body["ticker"].strip().upper()

        # Validate ticker format (1-5 alphanumeric characters)
        if not ticker or len(ticker) > 5 or not ticker.isalnum():
            return jsonify({"success": False, "error": "Invalid ticker format"}), 400

        # Load current data
        data = load_requests()

        # Increment count
        if ticker in data["requests"]:
            data["requests"][ticker] += 1
        else:
            data["requests"][ticker] = 1

        # Add to history
        data["history"].append({
            "ticker": ticker,
            "timestamp": datetime.now().isoformat(),
            "ip": request.remote_addr
        })

        # Save
        save_requests(data)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ticker request: ${ticker} (count: {data['requests'][ticker]})")

        return jsonify({
            "success": True,
            "ticker": ticker,
            "count": data["requests"][ticker]
        })

    except Exception as e:
        print(f"Error processing ticker request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ticker-requests", methods=["GET"])
def get_ticker_requests():
    """
    Get all ticker requests (admin endpoint).

    Returns:
        {"requests": {"AAPL": 3, "MSFT": 1}, "history": [...]}
    """
    data = load_requests()

    # Sort by count descending
    sorted_requests = dict(sorted(
        data["requests"].items(),
        key=lambda x: x[1],
        reverse=True
    ))

    return jsonify({
        "requests": sorted_requests,
        "total_requests": sum(data["requests"].values()),
        "unique_tickers": len(data["requests"]),
        "history": data.get("history", [])[-50:]  # Last 50 entries
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


def main():
    parser = argparse.ArgumentParser(description="Ticker Request Server")
    parser.add_argument("--port", type=int, default=5050, help="Port to run on (default: 5050)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    print(f"Starting Ticker Request Server on {args.host}:{args.port}")
    print(f"Requests will be saved to: {REQUESTS_FILE}")
    print()
    print("Endpoints:")
    print(f"  POST http://localhost:{args.port}/api/ticker-request")
    print(f"  GET  http://localhost:{args.port}/api/ticker-requests")
    print()

    app.run(host=args.host, port=args.port, debug=True)


if __name__ == "__main__":
    main()
