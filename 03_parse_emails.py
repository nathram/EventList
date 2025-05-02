import os
import json
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup
from datetime import datetime
import email.utils

def extract_email_data(eml_path):
    with open(eml_path, 'rb') as file:
        msg = BytesParser(policy=policy.default).parse(file)

    return {
        "subject": msg.get("subject", ""),
        "from": msg.get("from", ""),
        "date": msg.get("date", ""),
        "body": get_body(msg)
    }

def get_body(msg):
    if msg.is_multipart():
        body = ""
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
            if content_type == "text/html" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                body = clean_html(body)
                break
        return body
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        if "html" in msg.get_content_type().lower():
            body = clean_html(body)
        return body

def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    return ' '.join(soup.get_text().split())

def parse_email_date(date_str):
    """Convert date string to datetime, or None if invalid."""
    try:
        return email.utils.parsedate_to_datetime(date_str)
    except Exception:
        return None

def extract_all_emails(eml_dir, output_json):
    all_emails = []
    for filename in os.listdir(eml_dir):
        if filename.lower().endswith(".eml"):
            path = os.path.join(eml_dir, filename)
            data = extract_email_data(path)
            all_emails.append(data)

    # Sort by parsed date, most recent first; fallback to 1970 if missing
    all_emails.sort(key=lambda email: parse_email_date(email.get("date")) or datetime(1970, 1, 1), reverse=True)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_emails, f, indent=4, ensure_ascii=False)

# Example usage
extract_all_emails("saved_emails", "parsed_emails.json")
