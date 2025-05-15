import sqlite3
import json
import subprocess
import time
from tqdm import tqdm

# Prompt template for Ollama
def build_prompt(subject, body):
    return f"""
You are a helpful assistant that extracts structured information from emails that describe upcoming events.

Below is the content of one email. Use it to extract the following fields. Be precise, and if information is not clearly provided, write "unknown".

Email Subject:
{subject}

Email Body:
{body}

Extract and return the following as a JSON object with exactly these keys:

{{
  "event_name": [A short name or title of the event, if provided. Otherwise "unknown"],
  "description": [A brief summary of what the event is about, ideally 1-2 sentences.],
  "location": [The venue, building, room, or address where the event will take place. If online, say so. If not mentioned, write "unknown"],
  "date": [The date and time of the event in natural language (e.g., "Thursday at 6pm"). If not specified, write "unknown"],
  "registration_required": ["yes" if the email says you must register or RSVP before attending, "no" if not required, or "unknown" if unclear],
  "food_provided": [Mention the food being offered (e.g., "pizza", "light snacks", "catered dinner"). If no food will be provided, write "none". If the email doesn’t say, write "unknown"]
}}

Return only the JSON. Do not include any explanations or extra text.
"""

# Run a prompt through Ollama and return parsed JSON
def query_ollama(prompt, model="llama3"):
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=30
        )
        output = result.stdout.decode("utf-8")

        # Find first valid JSON block in output
        start = output.find("{")
        end = output.rfind("}") + 1
        json_str = output[start:end]
        return json.loads(json_str)

    except Exception as e:
        print("Failed to parse or run model:", e)
        return None

# Load emails from events DB
def load_emails():
    conn = sqlite3.connect("emails_events.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, body FROM emails")
    emails = cursor.fetchall()
    conn.close()
    return emails

# Save extracted info to a new database
def save_extracted(events):
    conn = sqlite3.connect("events_info.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS event_info (
            id INTEGER PRIMARY KEY,
            event_name TEXT,
            description TEXT,
            location TEXT,
            date TEXT,
            registration_required TEXT,
            food_provided TEXT
        )
    ''')

    for item in events:
        cursor.execute('''
            INSERT OR REPLACE INTO event_info
            (id, event_name, description, location, date, registration_required, food_provided)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            item['id'],
            item.get('event_name'),
            item.get('description'),
            item.get('location'),
            item.get('date'),
            item.get('registration_required'),
            item.get('food_provided')
        ))

    conn.commit()
    conn.close()

def main():
    emails = load_emails()
    extracted = []

    for email in tqdm(emails, desc="Extracting info"):
        id_, subject, body = email
        prompt = build_prompt(subject, body)
        info = query_ollama(prompt)

        if info:
            info['id'] = id_
            extracted.append(info)
        time.sleep(1)  # prevent overload if needed

    save_extracted(extracted)
    print(f"Extracted structured info from {len(extracted)} emails into 'events_info.db'.")

if __name__ == "__main__":
    main()
