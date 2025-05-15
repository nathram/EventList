import sqlite3
import pandas as pd
import joblib

def load_unlabeled_emails():
    conn = sqlite3.connect("emails.db")
    df = pd.read_sql_query("SELECT subject, sender, date, body FROM emails", conn)
    conn.close()
    return df

def save_events_to_new_db(events_df):
    conn = sqlite3.connect("emails_events.db")
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            sender TEXT,
            date TEXT,
            body TEXT
        )
    ''')

    # Insert rows without specifying id (let SQLite auto-increment)
    for _, row in events_df.iterrows():
        cursor.execute('''
            INSERT INTO emails (subject, sender, date, body)
            VALUES (?, ?, ?, ?)
        ''', (row['subject'], row['sender'], row['date'], row['body']))

    conn.commit()
    conn.close()

def main():
    # Load trained model
    model = joblib.load("event_classifier.pkl")

    # Load unlabeled emails
    df = load_unlabeled_emails()
    X = df['subject'] + " " + df['body']

    # Predict
    predictions = model.predict(X)

    # Filter for events
    df['is_event'] = predictions
    events_df = df[df['is_event'] == 1].drop(columns='is_event')

    # Save to new database
    save_events_to_new_db(events_df)
    print(f"Exported {len(events_df)} emails classified as events to 'emails_events.db'.")

if __name__ == "__main__":
    main()
