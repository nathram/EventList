import os
import json
from email import policy
from email.parser import BytesParser
from bs4 import BeautifulSoup

def extract_email_data(eml_path):
    with open(eml_path, 'rb') as file:
        msg = BytesParser(policy=policy.default).parse(file)
    
    # Extract data
    return {
        "subject": msg.get("subject", ""),
        "from": msg.get("from", ""),
        "date": msg.get("date", ""),
        "body": get_body(msg)
    }

def get_body(msg):
    # If the message is multipart (contains attachments, images, etc.)
    if msg.is_multipart():
        body = ""
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            # Handle plain text parts
            if content_type == "text/plain" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
            
            # Handle HTML parts (if any)
            if content_type == "text/html" and "attachment" not in content_disposition:
                body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                # Clean the HTML
                body = clean_html(body)
                break
        return body
    
    # If it's not multipart, it's a simple text or HTML email
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
        # Check if it's HTML content
        if "html" in msg.get_content_type().lower():
            body = clean_html(body)
        return body

def clean_html(html_content):
    """Remove unnecessary HTML tags and scripts/styles."""
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove script and style elements
    for script_or_style in soup(['script', 'style']):
        script_or_style.decompose()
    
    # Get the text from the HTML, removing all other tags
    clean_text = soup.get_text()
    
    # Optionally, clean up extra whitespace, newlines, etc.
    return ' '.join(clean_text.split())

def extract_all_emails(eml_dir, output_json):
    all_emails = []
    for filename in os.listdir(eml_dir):
        if filename.lower().endswith(".eml"):
            path = os.path.join(eml_dir, filename)
            data = extract_email_data(path)
            all_emails.append(data)
    
    # Save to JSON
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(all_emails, f, indent=4, ensure_ascii=False)

# Example usage
extract_all_emails("saved_emails", "parsed_emails.json")
