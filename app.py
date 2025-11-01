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
        "Authorization": f"Bearer {NOTION_TOKEN}",
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
    # Query the database
    payload = {
        "filter": {},  # You can add filters here if needed
        "sorts": [{"timestamp": "created_time", "direction": "descending"}]
    }
    
    resp = requests.post(
        f"{NOTION_BASE}/databases/{DATABASE_ID}/query",
        headers=notion_headers(),
        json=payload
    )

    if resp.status_code >= 300:
        return jsonify({"ok": False, "error": resp.text}), resp.status_code

    return jsonify({"ok": True, "results": resp.json().get("results", [])})

@app.route("/create", methods=["POST"])
def create():
    data = request.get_json(force=True) or {}
    title = data.get("title")
    content = data.get("content")
    tags = data.get("tags") or []
    date_str = data.get("date")

    # default date = today (ISO)
    if not date_str:
        date_str = dt.date.today().isoformat()

    payload = build_page_payload(title, content, tags, date_str)
    resp = requests.post(f"{NOTION_BASE}/pages", headers=notion_headers(), json=payload)

    if resp.status_code >= 300:
        return jsonify({"ok": False, "error": resp.text}), resp.status_code

    return jsonify({"ok": True, "result": resp.json()})

if __name__ == "__main__":
    # Allow external access and enable debug mode
    app.run(host="0.0.0.0", port=5000, debug=True)
