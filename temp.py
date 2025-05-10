import json
import sqlite3
import sys
import os


# Connect to SQLite database
conn = sqlite3.connect("emails.db")
cursor = conn.cursor()

cursor.execute("""
DELETE FROM emails
WHERE rowid IN (
    SELECT rowid FROM emails
    ORDER BY date DESC
    LIMIT 3
)
""")
conn.commit()
