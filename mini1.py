from playwright.sync_api import sync_playwright
from getpass import getpass
import time, os

# Prompt user for KERBEROS (username) and PASSWORD
KERBEROS = input("Enter your KERBEROS (MIT username): ")
EMAIL = KERBEROS + "@mit.edu"
PASSWORD = getpass("Enter your password: ")  # Hides the input for security
DOWNLOAD_DIR = "saved_emails"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def run():
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
        NUM_EMAILS_TO_DOWNLOAD = 30
        seen_ids = set()
        downloaded_count = 0
        max_scrolls = 100

        print("Waiting for inbox to load...")
        page.wait_for_selector('[data-convid]', timeout=60000)
        print("Inbox loaded.")

        for _ in range(max_scrolls):
            emails = page.query_selector_all('[data-convid]')
            print("emails grabbed: " + str(len(emails)))

            for email in emails:
                cid = email.get_attribute("data-convid")
                if not cid or cid in seen_ids:
                    continue

                seen_ids.add(cid)

                try:
                    # Re-select the element just before interacting with it
                    email_fresh = page.query_selector(f'[data-convid="{cid}"]')
                    if not email_fresh:
                        print(f"⚠️ Skipping email {cid} (element no longer in DOM)")
                        continue

                    email_fresh.click()
                    page.wait_for_timeout(2000)

                    # Click the "More actions" (three dots) button
                    page.click('button[aria-label="More actions"]')
                    page.wait_for_timeout(500)

                    # Click "Download"
                    page.click('button[aria-label="Download"]')
                    page.wait_for_timeout(500)

                    # Wait for and click "Download as EML"
                    with page.expect_download() as download_info:
                        page.click('button[aria-label="Download as EML"]')

                    download = download_info.value
                    filepath = f"{DOWNLOAD_DIR}/{cid}.eml"
                    download.save_as(filepath)
                    print(f"✅ Saved {filepath}")
                    downloaded_count += 1

                    if downloaded_count >= NUM_EMAILS_TO_DOWNLOAD:
                        break

                except Exception as e:
                    print(f"❌ Error downloading email {downloaded_count + 1}: {e}")

            if downloaded_count >= NUM_EMAILS_TO_DOWNLOAD:
                break

            page.keyboard.press("PageDown")
            time.sleep(1)

        print(f"✅ Finished downloading {downloaded_count} emails.")
        browser.close()

run()
