import os
import json
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from bs4 import BeautifulSoup

def extract_email_data(eml_path):
    with open(eml_path, 'rb') as file:
        msg = BytesParser(policy=policy.default).parse(file)

    # Prefer 'X-Mailman-Approved-At' over 'Date'
    date_header = msg.get("X-Mailman-Approved-At") or msg.get("Date") or ""

    return {
        "subject": msg.get("subject", ""),
        "from": msg.get("from", ""),
        "date": date_header,
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
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def extract_all_emails(eml_dir, output_json):
    all_emails = []
    for filename in os.listdir(eml_dir):
        if filename.lower().endswith(".eml"):
            path = os.path.join(eml_dir, filename)
            data = extract_email_data(path)
            all_emails.append(data)

    # Sort emails from most recent to oldest
    all_emails.sort(
        key=lambda email: parse_email_date(email.get("date")) or datetime(1970, 1, 1, tzinfo=timezone.utc),
        reverse=True
    )

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_emails, f, indent=4, ensure_ascii=False)

# Example usage
extract_all_emails("saved_emails", "parsed_emails.json")
