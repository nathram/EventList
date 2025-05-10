from playwright.sync_api import sync_playwright
from getpass import getpass
import time, os, json, re, sys, sqlite3, pytz
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta
from dateutil import parser
from bs4 import BeautifulSoup

# Prompt user for KERBEROS (username) and PASSWORD
KERBEROS = input("Enter your KERBEROS (MIT username): ")
EMAIL = KERBEROS + "@mit.edu"
PASSWORD = getpass("Enter your password: ")  # Hides the input for security
DOWNLOAD_DIR = "saved_emails"
OUTPUT_JSON = "parsed_emails.json"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Connect to SQLite database
conn = sqlite3.connect("emails.db")
cursor = conn.cursor()

# Create table if not exists
cursor.execute(f'''
    CREATE TABLE IF NOT EXISTS {"emails"} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT,
        sender TEXT,
        date TEXT,
        body TEXT
    )
''')

def extract_email_data(eml_path, threshold):
    with open(eml_path, 'rb') as file:
        msg = BytesParser(policy=policy.default).parse(file)

    # Prefer 'X-Mailman-Approved-At' over 'Date'
    date_header = msg.get("X-Mailman-Approved-At") or msg.get("Date") or ""
    subject = msg.get("subject", "")
    body = get_body(msg)

    # Split the body into original and replies
    split_messages = split_replies(body)

    parsed_messages = []
    for i, segment in enumerate(split_messages):
        # Use known subject to remove reply header chunk in later segments

        # Adjust subject only for the first message
        final_subject = subject if i == 0 and not subject.startswith("Re: ") else subject[4:]
        
        if i == 0:
            cleaned_segment = segment.strip()
        else:
            cleaned_segment = strip_leading_headers(segment, final_subject)

        # Extract date
        segment_date = extract_reply_date(segment) or (format_email_header_date(date_header) if i == 0 else date_from_headers(segment))

        threshold_datetime = datetime.strptime(threshold, "%a %m/%d/%Y %I:%M %p")
        segment_datetime = datetime.strptime(segment_date, "%a %m/%d/%Y %I:%M %p")

        # Compare
        if threshold_datetime > segment_datetime:
            continue

        parsed_messages.append({
            "subject": final_subject,
            "from": msg.get("from", ""),
            "date": segment_date,
            "body": cleaned_segment
        })

    return parsed_messages

def strip_leading_headers(segment, subject):
    """
    Removes everything up to and including the Subject: ...<actual subject> part.
    Only applies if the subject is found.
    """
    if not subject:
        return segment.strip()
    
    # Escape special characters in subject for regex
    escaped_subject = re.escape(subject)
    
    # Look for the full subject line like "Subject: [USWIM] Board Games & Pizza 🍕"
    match = re.search(rf"Subject:\s*{escaped_subject}", segment)
    if match:
        # Remove everything up to the end of the Subject line
        return segment[match.end():].strip()
    
    return segment.strip()

def date_from_headers(segment):
    """
    Extracts and parses the datetime from a 'Sent: ...' line that is followed by 'To:'.
    Returns an ISO formatted datetime string or None.
    """
    match = re.search(r"Sent:\s*(.+?)\s*To:", segment)
    if match:
        raw_date = match.group(1).strip()
        try:
            dt = parser.parse(raw_date)
            hour_str = dt.strftime('%I').lstrip('0') or '0'
            return f"{dt.strftime('%a')} {dt.month}/{dt.day}/{dt.year} {hour_str}:{dt.strftime('%M %p')}"
        except Exception:
            return None
    return None

def format_email_header_date(date_str):
    """
    Convert an RFC 2822 date string (e.g. 'Fri, 09 May 2025 20:00:00 +0000')
    to the format 'Fri 5/9/2025 8:00 PM'.
    """
    try:
        dt = parsedate_to_datetime(date_str)
        hour_str = dt.strftime('%I').lstrip('0') or '0'
        return f"{dt.strftime('%a')} {dt.month}/{dt.day}/{dt.year} {hour_str}:{dt.strftime('%M %p')}"
    except Exception:
        return date_str  # fallback to original if parsing fails

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

def split_replies(body):
    # Refined reply patterns to split right before the "From: ..." section or other reply markers
    reply_patterns = [
        r'(?=From:.+)',  # Split right before 'From:' which usually indicates a reply
    ]
    
    # Compile the regex pattern
    pattern = re.compile("|".join(reply_patterns), flags=re.MULTILINE)
    
    # Split the body text where the patterns match
    split_body = pattern.split(body)
    
    # Return the cleaned split body (without leading empty strings)
    return [part.strip() for part in split_body if part.strip()]


def extract_reply_date(text):
    # Try to extract datetime from a line like "On Mon, Apr 1, 2024 at 5:12 PM John Doe <jdoe@example.com> wrote:"
    match = re.search(r'^On (.+?) wrote:', text, re.MULTILINE)
    if match:
        raw_date = match.group(1)
        try:
            # Strip email addresses to improve parse accuracy
            raw_date = re.sub(r'<.*?>', '', raw_date)
            dt = parsedate_to_datetime(raw_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except Exception:
            return None
    return None


def parse_email_date(date_str):
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def run():
    # Step 0: Determine date threshold for fetching emails
    cursor.execute("SELECT date FROM emails ORDER BY date DESC LIMIT 1")
    result = cursor.fetchone()

    # Get local timezone explicitly as US/Eastern
    local_tz = pytz.timezone("US/Eastern")

    if result is None:
        print("First time user! Backing up.")
        threshold_dt = datetime.now(local_tz) - timedelta(days=1095)
    else:
        # Parse the latest date from the DB
        latest_stored = result[0]
        try:
            threshold_dt = parser.parse(latest_stored)
            if threshold_dt.tzinfo is None:
                threshold_dt = threshold_dt.replace(tzinfo=local_tz)
            else:
                threshold_dt = threshold_dt.astimezone(local_tz)
            print(f"Latest email in database is from {threshold_dt.isoformat()}")
        except Exception:
            print("⚠️ Could not parse latest stored date..")
            threshold_dt = datetime.now(local_tz) - timedelta(days=1095)

    # Format threshold_dt to "Fri 5/10/2025 11:14 PM"
    threshold_dt = threshold_dt.strftime("%a %-m/%-d/%Y %-I:%M %p")
    print("thresh " + threshold_dt)

    all_emails = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://outlook.office.com/mail/")

        # Step 1: Login
        page.wait_for_selector('input[type="email"]', timeout=10000)
        page.fill('input[type="email"]', '')
        page.type('input[type="email"]', EMAIL)
        page.press('input[type="email"]', 'Enter')

        print("Email entered, moving to MIT Touchstone Page")
        time.sleep(10)

        page.wait_for_selector('input[name="identifier"]', timeout=10000)
        page.fill('input[name="identifier"]', '')
        page.type('input[name="identifier"]', KERBEROS)
        page.press('input[name="identifier"]', 'Enter')

        print("Kerberos entered, moving to password")
        time.sleep(10)

        page.wait_for_selector('input[name="credentials.passcode"]', timeout=10000)
        page.fill('input[name="credentials.passcode"]', '')
        page.type('input[name="credentials.passcode"]', PASSWORD)
        page.press('input[name="credentials.passcode"]', 'Enter')

        print("Password entered, moving to Duo MFA")
        print("Please wait for Duo Push to your device...")
        page.wait_for_timeout(20000)

        try:
            page.wait_for_selector('#trust-browser-button', timeout=15000)
            page.click('#trust-browser-button')
            print("Clicked 'Yes, this is my device'")
        except:
            print("No 'Is this your device' prompt found — continuing")

        page.wait_for_url("https://outlook.office.com/mail/*", timeout=60000)
        print("Login successful!")

        # Step 2: Scroll and extract messages
        seen_ids = set()
        downloaded_count = 0
        max_scrolls = 100000

        print("Waiting for inbox to load...")
        page.wait_for_selector('[data-convid]', timeout=60000)
        print("Inbox loaded.")

        reached_threshold = False

        for _ in range(max_scrolls):
            emails = page.query_selector_all('[data-convid]')
            print("emails grabbed: " + str(len(emails)))
            total_skipped = 0

            for email in emails:
                cid = email.get_attribute("data-convid")
                if not cid or cid in seen_ids:
                    total_skipped += 1
                    if total_skipped == len(emails):
                        reached_threshold = True
                    continue

                seen_ids.add(cid)

                
                email_fresh = page.query_selector(f'[data-convid="{cid}"]')
                if not email_fresh:
                    print(f"⚠️ Skipping email {cid} (element no longer in DOM)")
                    continue

                email_fresh.click()
                page.wait_for_timeout(2000)

                page.click('button[aria-label="More actions"]')
                page.wait_for_timeout(500)
                page.click('button[aria-label="Download"]')
                page.wait_for_timeout(500)

                with page.expect_download() as download_info:
                    page.click('button[aria-label="Download as EML"]')

                download = download_info.value
                filepath = f"{DOWNLOAD_DIR}/{cid}.eml"
                download.save_as(filepath)

                # ✅ Get visible date from page
                try:
                    dom_date = page.locator('[data-testid="SentReceivedSavedTime"]').text_content(timeout=5000)
                except:
                    dom_date = ""

                # ✅ Parse and store email data (override date for original email with DOM date)
                parsed_segments = extract_email_data(filepath, threshold_dt)
                if dom_date and parsed_segments:
                    parsed_segments[0]["date"] = dom_date

                if parsed_segments:
                    all_emails.extend(parsed_segments)
                else:
                    reached_threshold = True
                    break

                # ✅ Delete .eml file
                os.remove(filepath)
                print(f"✅ Saved and parsed {filepath} ({len(parsed_segments)} part(s))")
                downloaded_count += 1

            if reached_threshold:
                break

            page.keyboard.press("PageDown")
            time.sleep(1)

        print(f"✅ Finished downloading and parsing {downloaded_count} emails.")
        browser.close()

    # Sort emails by date, most recent first
    all_emails.sort(
        key=lambda email: parse_email_date(email.get("date")) or datetime(1970, 1, 1, tzinfo=timezone.utc),
        reverse=True
    )

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_emails, f, indent=4, ensure_ascii=False)
    print(f"📄 Saved all parsed emails to {OUTPUT_JSON}")

run()
