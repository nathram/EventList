import sqlite3
import os

DB_NAME = "emails_labeled.db"

def setup_db():
    # Ensure copy exists
    if not os.path.exists(DB_NAME):
        import shutil
        shutil.copy("emails.db", DB_NAME)
        print(f"Copied 'emails.db' → '{DB_NAME}'")

    # Add is_event column if it doesn't exist
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE emails ADD COLUMN is_event INTEGER;")
        conn.commit()
    except sqlite3.OperationalError:
        # Column probably already exists
        pass
    conn.close()

def label_emails():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Select 270 earliest emails by date that haven't been labeled
    cursor.execute("""
        SELECT id, subject, sender, date, body 
        FROM emails 
        WHERE is_event IS NULL 
        ORDER BY datetime(date) ASC 
        LIMIT 270;
    """)
    rows = cursor.fetchall()

    for row in rows:
        id_, subject, sender, date, body = row

        print("\n" + "="*60)
        print(f"ID: {id_}")
        print(f"From: {sender}")
        print(f"Date: {date}")
        print(f"Subject: {subject}")
        print(f"Body:\n{body[:500]}")  # truncate for readability
        print("="*60)
        
        while True:
            label = input("Is this about an upcoming event? [1 = Yes, 0 = No, s = skip, q = quit] ").strip().lower()
            if label in {"1", "0"}:
                cursor.execute("UPDATE emails SET is_event = ? WHERE id = ?", (int(label), id_))
                conn.commit()
                break
            elif label == "s":
                break
            elif label == "q":
                conn.commit()
                conn.close()
                print("Exiting early.")
                return
            else:
                print("Invalid input. Please enter 1, 0, s, or q.")

    conn.commit()
    conn.close()
    print("Finished labeling 270 earliest emails.")

if __name__ == "__main__":
    setup_db()
    label_emails()
