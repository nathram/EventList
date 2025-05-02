from playwright.sync_api import sync_playwright
from getpass import getpass
import time, os
import json


# Prompt user for KERBEROS (username) and PASSWORD
KERBEROS = input("Enter your KERBEROS (MIT username): ")
EMAIL = KERBEROS + "@mit.edu"
PASSWORD = getpass("Enter your password: ")  # Hides the input for security
DOWNLOAD_DIR = "saved_emails"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def save_email(subject, body, index):
    # Save as .html for now (Outlook doesn’t offer native .eml download)
    safe_subject = "".join(c if c.isalnum() else "_" for c in subject)[:50]
    filename = f"{index:04}_{safe_subject}.html"
    with open(os.path.join(DOWNLOAD_DIR, filename), "w", encoding="utf-8") as f:
        f.write(body)

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # or False if using xvfb
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://outlook.office.com/mail/")

        # Step 1: Enter school email and submit
        page.wait_for_selector('input[type="email"]', timeout=10000)
        page.fill('input[type="email"]', '')
        page.type('input[type="email"]', EMAIL)
        page.press('input[type="email"]', 'Enter')
        #page.click('input[type="submit"]')

        time.sleep(10)
        print("Email entered, moving to MIT Touchstone Page")  # optional, helpful for visibility

        # After redirect to Okta
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

        # Step 4: Duo MFA — wait for prompt
        print("Please wait for Duo Push to your device...")
        page.wait_for_timeout(20000)  # Give time to approve push on phone

        # Step 4.5: Handle "Is this your device?" prompt
        try:
            page.wait_for_selector('#trust-browser-button', timeout=15000)
            page.click('#trust-browser-button')
            print("Clicked 'Yes, this is my device'")
        except:
            print("No 'Is this your device' prompt found — continuing")


        # You can optionally screenshot or debug:
        # page.screenshot(path="duo.png")
        # print(page.content())
        # Once Duo is complete, redirect back to Outlook
        page.wait_for_url("https://outlook.office.com/mail/*", timeout=60000)

        print("Login successful!")

        # [continue extracting emails here...]

        # Step 2: Extract messages (this is simplified; actual selectors may vary)
        # Wait for the inbox to load
        print("Waiting for inbox to load...")
        page.wait_for_selector('[data-convid]', timeout=60000)
        print("Inbox loaded.")
        
        emails = page.query_selector_all('[data-convid]')

        for idx, email in enumerate(emails[:5]):  # Adjust number as needed
            try:
                email.click()
                page.wait_for_timeout(2000)

                # Step 1: Click the "More actions" (three dots) button
                page.click('button[aria-label="More actions"]')
                page.wait_for_timeout(500)

                # Step 2: Click "Download"
                page.click('button[aria-label="Download"]')
                page.wait_for_timeout(500)

                # Step 3: Wait for and click "Download as EML"
                with page.expect_download() as download_info:
                    page.click('button[aria-label="Download as EML"]')

                download = download_info.value
                filepath = f"saved_emails/email_{idx+1}.eml"
                download.save_as(filepath)
                print(f"✅ Saved {filepath}")

            except Exception as e:
                print(f"❌ Error downloading email {idx}: {e}")




        browser.close()

run()
