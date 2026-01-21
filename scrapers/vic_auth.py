"""
VIC Authentication Module
Handles login to Value Investors Club using Playwright for JS support.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
COOKIES_FILE = PROJECT_ROOT / "data" / "vic_cookies.json"

# Credentials
VIC_LOGIN_URL = "https://www.valueinvestorsclub.com/login"
VIC_IDEAS_URL = "https://www.valueinvestorsclub.com/ideas"
USERNAME = "VICloginname"
PASSWORD = "Spring2016"


def save_cookies(context: BrowserContext) -> None:
    """Save browser cookies to file for session reuse."""
    cookies = context.cookies()
    COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Cookies saved to {COOKIES_FILE}")


def load_cookies(context: BrowserContext) -> bool:
    """Load cookies from file if they exist."""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print("Loaded existing cookies")
        return True
    return False


def login(page) -> bool:
    """
    Perform login to VIC.
    Returns True if login successful.
    """
    page.goto(VIC_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)

    # Wait for login form to be ready
    page.wait_for_selector("input[name='login[login_name]']", timeout=15000)

    # VIC uses specific field names
    username_input = page.query_selector("input[name='login[login_name]']")
    password_input = page.query_selector("input[name='login[password]']")

    if not username_input or not password_input:
        print("Could not find login form fields")
        return False

    # Fill credentials
    username_input.fill(USERNAME)
    password_input.fill(PASSWORD)

    # Wait for Cloudflare Turnstile to complete (if present)
    # This may require user interaction in headed mode
    print("Waiting for Cloudflare verification...")
    page.wait_for_timeout(3000)

    # Check if turnstile needs manual solving
    turnstile = page.query_selector("iframe[src*='turnstile']")
    if turnstile:
        print("Cloudflare Turnstile detected - please complete verification in browser...")
        # Wait for turnstile to be solved (response field gets populated)
        try:
            page.wait_for_function(
                "document.querySelector('input[name=\"cf-turnstile-response\"]')?.value?.length > 0",
                timeout=60000
            )
            print("Turnstile verified!")
        except:
            print("Turnstile timeout - may need manual intervention")

    # Find and click submit button (VIC uses id="login_btn")
    submit_btn = page.query_selector("#login_btn")
    if not submit_btn:
        submit_btn = page.query_selector("button[type='submit']")
    if not submit_btn:
        submit_btn = page.query_selector("form button")

    if submit_btn:
        submit_btn.click()
    else:
        # Try pressing Enter as fallback
        password_input.press("Enter")

    # Wait for navigation after login
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)  # Allow redirects to complete

    # Verify login success by checking if we're no longer on login page
    # or if we can access ideas
    current_url = page.url
    if "login" not in current_url.lower():
        print(f"Login successful! Redirected to: {current_url}")
        return True

    # Try navigating to ideas page to verify
    page.goto(VIC_IDEAS_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)

    # Check for members-only content indicator
    content = page.content()
    if "investment ideas" in content.lower() or "eligible" not in content.lower():
        print("Login verified - can access ideas")
        return True

    print("Login may have failed - please verify credentials")
    return False


def is_authenticated(page) -> bool:
    """Check if current session is authenticated."""
    page.goto(VIC_IDEAS_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2000)  # Let JS render
    content = page.content()
    # Authenticated users see logout link or profile menu
    return "log out" in content.lower() or "logout" in content.lower() or "my profile" in content.lower()


class VICSession:
    """
    Context manager for authenticated VIC browsing.

    Usage:
        with VICSession() as (browser, page):
            page.goto("https://www.valueinvestorsclub.com/ideas")
            # ... scrape content
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=self.headless)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)

        # Try loading existing cookies
        cookies_loaded = load_cookies(self.context)
        if cookies_loaded:
            print("Loaded existing cookies")
        else:
            print("No cookies found - proceeding without authentication")

        return self.browser, self.page

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()


def test_auth():
    """Test authentication module."""
    print("Testing VIC authentication...")

    with VICSession(headless=False) as (browser, page):
        page.goto(VIC_IDEAS_URL)
        print(f"Current URL: {page.url}")
        print(f"Page title: {page.title()}")

        # Take a screenshot for verification
        screenshot_path = PROJECT_ROOT / "data" / "auth_test.png"
        page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved to {screenshot_path}")

        input("Press Enter to close browser...")


if __name__ == "__main__":
    test_auth()
