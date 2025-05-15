import json
import sqlite3
import sys
import os
from datetime import datetime

def parse_date(date_str):
    """Convert 'Wed 5/14/2025 6:19 PM' to '2025-05-14 18:19:00'"""
    try:
        dt = datetime.strptime(date_str, "%a %m/%d/%Y %I:%M %p")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str  # fallback if parsing fails

def json_to_sqlite():
    # Load JSON data
    with open("parsed_emails.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Connect to SQLite database
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    # Get the current max ID
    cursor.execute("SELECT MAX(id) FROM emails;")
    result = cursor.fetchone()
    current_max_id = result[0] if result[0] is not None else 0
    next_id = current_max_id + 1

    # Insert entries with manual ID
    for i, item in enumerate(data):
        subject = item.get("subject", "")
        sender = item.get("from", "")
        raw_date = item.get("date", "")
        formatted_date = parse_date(raw_date)
        body = item.get("body", "")
        email_id = next_id + i

        cursor.execute('''
            INSERT INTO emails (id, subject, sender, date, body)
            VALUES (?, ?, ?, ?, ?)
        ''', (email_id, subject, sender, formatted_date, body))

    # Commit and close
    conn.commit()
    conn.close()
    print(f"Inserted {len(data)} entries into 'emails.db' in table 'emails'.")

if __name__ == "__main__":
    json_to_sqlite()

    # if os.path.exists("parsed_emails.json"):
    #     os.remove("parsed_emails.json")
