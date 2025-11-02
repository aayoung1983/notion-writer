# app.py
import os
import datetime as dt
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

app = Flask(__name__)

NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"  # stable for basic ops

def notion_headers():
    return {
        "Authorization": NOTION_TOKEN,  # Try without Bearer prefix
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

def build_page_payload(title, content, tags=None, date_str=None):
    # Adjust property names to match your DB (Title, Tags, Date, Content)
    props = {
        "Title": {"title": [{"text": {"content": title or "Untitled"}}]},
    }

    if tags:
        props["Tags"] = {"multi_select": [{"name": t} for t in tags]}

    if date_str:
        props["Date"] = {"date": {"start": date_str}}

    children = []
    if content:
        children = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                },
            }
        ]

    return {
        "parent": {"database_id": DATABASE_ID},
        "properties": props,
        "children": children,
    }

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

@app.route("/read", methods=["GET"])
def read_database():
    if not NOTION_TOKEN:
        return jsonify({"error": "NOTION_TOKEN not set"}), 500
    if not DATABASE_ID:
        return jsonify({"error": "DATABASE_ID not set"}), 500

    print(f"Using token: {NOTION_TOKEN[:10]}...")  # Print first 10 chars of token
    print(f"Database ID: {DATABASE_ID}")
    
    # Query the database
    payload = {
        "filter": {},  # You can add filters here if needed
        "sorts": [{"timestamp": "created_time", "direction": "descending"}]
    }
    
    headers = notion_headers()
    print(f"Request headers: {headers}")
    print(f"Request payload: {payload}")
    
    try:
        resp = requests.post(
            f"{NOTION_BASE}/databases/{DATABASE_ID}/query",
            headers=headers,
            json=payload
        )
        print(f"Response status: {resp.status_code}")
        print(f"Response body: {resp.text}")

    if resp.status_code >= 300:
        return jsonify({"ok": False, "error": resp.text}), resp.status_code

    return jsonify({"ok": True, "results": resp.json().get("results", [])})

@app.route("/create", methods=["POST"])
def create():
    if not NOTION_TOKEN:
        return jsonify({"ok": False, "error": "NOTION_TOKEN environment variable is not set"}), 500
    if not DATABASE_ID:
        return jsonify({"ok": False, "error": "NOTION_DATABASE_ID environment variable is not set"}), 500

    try:
        data = request.get_json(force=True) or {}
        title = data.get("title")
        content = data.get("content")
        tags = data.get("tags") or []
        date_str = data.get("date")

        # default date = today (ISO)
        if not date_str:
            date_str = dt.date.today().isoformat()

        payload = build_page_payload(title, content, tags, date_str)
        headers = notion_headers()
        
        # Debug info
        print(f"Making request to Notion API with token: {NOTION_TOKEN[:4]}...")
        print(f"Database ID: {DATABASE_ID}")
        print(f"Headers: {headers}")
        print(f"Payload: {payload}")
        
        resp = requests.post(f"{NOTION_BASE}/pages", headers=headers, json=payload)
        
        if resp.status_code >= 300:
            error_text = resp.text
            print(f"Notion API Error: {error_text}")
            return jsonify({"ok": False, "error": error_text, "status_code": resp.status_code}), resp.status_code

        return jsonify({"ok": True, "result": resp.json()})
    except Exception as e:
        print(f"Error in create endpoint: {str(e)}")
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    # Allow external access and enable debug mode
    app.run(host="0.0.0.0", port=5000, debug=True)
