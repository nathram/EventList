import json
import sqlite3
import sys
import os

def json_to_sqlite():
    # Load JSON data
    with open("parsed_emails.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Connect to SQLite database
    conn = sqlite3.connect("emails.db")
    cursor = conn.cursor()

    # Insert entries
    for item in data:
        cursor.execute(f'''
            INSERT INTO {"emails"} (subject, sender, date, body)
            VALUES (?, ?, ?, ?)
        ''', (item.get("subject", ""), item.get("from", ""), item.get("date", ""), item.get("body", "")))

    # Commit and close
    conn.commit()
    conn.close()
    print(f"Inserted {len(data)} entries into '{"emails.db"}' in table '{"emails"}'.")

if __name__ == "__main__":

    json_to_sqlite()

    if os.path.exists("parsed_emails.json"):
        os.remove("parsed_emails.json")