"""
Quicken Simplifi Browser Automation Client
Handles authentication and web scraping using Playwright
All code is self-contained with no third-party API dependencies
"""

import os
import time
import json
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, Playwright
from bs4 import BeautifulSoup


class SimplifiClient:
    """Client for interacting with Quicken Simplifi using browser automation"""

    BASE_URL = "https://app.simplifimoney.com"
    LOGIN_URL = f"{BASE_URL}/login"
    TRANSACTIONS_URL = f"{BASE_URL}/transactions"

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None, headless: bool = True):
        """
        Initialize the Simplifi client with browser automation

        Args:
            email: Simplifi account email
            password: Simplifi account password
            headless: Run browser in headless mode (default: True)
        """
        self.email = email or os.getenv('SIMPLIFI_EMAIL')
        self.password = password or os.getenv('SIMPLIFI_PASSWORD')
        self.headless = headless

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False

    async def __aenter__(self):
        """Async context manager entry"""
        await self._start_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _start_browser(self):
        """Start the Playwright browser"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
            # Enhanced security configuration for browser context
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                # Remove user agent spoofing for transparency
                ignore_https_errors=False,  # Enforce SSL validation
                java_script_enabled=True,
                accept_downloads=False,  # Prevent unexpected file downloads
                bypass_csp=False,  # Respect Content Security Policy
                locale='en-US',
                timezone_id='America/New_York',
                record_video_dir=None,  # Don't record sensitive sessions
                record_har_path=None,  # Don't record network traffic
            )
            # Set reasonable timeout for network requests
            self.context.set_default_timeout(30000)  # 30 seconds
            self.page = await self.context.new_page()

    async def close(self):
        """Close the browser and cleanup resources"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None
        self.is_logged_in = False

    async def login(self) -> bool:
        """
        Authenticate with Quicken Simplifi using browser automation

        Returns:
            True if login successful, False otherwise
        """
        if not self.email or not self.password:
            raise ValueError("Email and password are required for authentication")

        try:
            if not self.page:
                await self._start_browser()

            print(f"Navigating to login page...")
            await self.page.goto(self.LOGIN_URL, wait_until='networkidle')

            # Wait for login form to be visible
            print("Waiting for login form...")
            await self.page.wait_for_selector('input[type="email"], input[name="email"]', timeout=10000)

            # Fill in email
            print("Entering credentials...")
            email_selector = 'input[type="email"], input[name="email"]'
            await self.page.fill(email_selector, self.email)

            # Fill in password
            password_selector = 'input[type="password"], input[name="password"]'
            await self.page.fill(password_selector, self.password)

            # Submit the form
            print("Submitting login form...")
            submit_button = 'button[type="submit"], button:has-text("Log in"), button:has-text("Sign in")'
            await self.page.click(submit_button)

            # Wait for navigation after login
            # We'll wait for either the dashboard or an error message
            try:
                # Wait for post-login page to load
                await self.page.wait_for_load_state('networkidle', timeout=15000)

                # Check if we're logged in by looking for common dashboard elements
                # This might need adjustment based on actual Simplifi UI
                await asyncio.sleep(2)  # Give page time to fully render

                current_url = self.page.url
                if 'login' not in current_url.lower() or 'dashboard' in current_url.lower():
                    print("✓ Login successful")
                    self.is_logged_in = True
                    return True
                else:
                    print("✗ Login failed - still on login page")
                    return False

            except Exception as e:
                print(f"Error during login verification: {e}")
                return False

        except Exception as e:
            print(f"Login failed: {e}")
            return False

    async def wait_for_2fa(self, timeout: int = 120):
        """
        Wait for user to complete 2FA manually

        Args:
            timeout: Maximum time to wait in seconds (default: 120)
        """
        print(f"\n{'='*60}")
        print("TWO-FACTOR AUTHENTICATION REQUIRED")
        print(f"{'='*60}")
        print("Please complete the 2FA verification in the browser window.")
        print(f"Waiting up to {timeout} seconds...")
        print(f"{'='*60}\n")

        start_time = time.time()
        while time.time() - start_time < timeout:
            current_url = self.page.url
            if 'login' not in current_url.lower() or 'dashboard' in current_url.lower():
                print("✓ 2FA completed successfully")
                self.is_logged_in = True
                return True
            await asyncio.sleep(1)

        print("✗ 2FA timeout")
        return False

    async def navigate_to_transactions(self):
        """Navigate to the transactions page"""
        if not self.is_logged_in:
            raise ValueError("Must be logged in first")

        print("Navigating to transactions page...")
        await self.page.goto(self.TRANSACTIONS_URL, wait_until='networkidle')
        await asyncio.sleep(2)  # Allow page to fully load

    async def get_accounts(self) -> List[Dict]:
        """
        Retrieve all accounts by scraping the accounts page

        Returns:
            List of account dictionaries
        """
        if not self.is_logged_in:
            raise ValueError("Must be logged in to retrieve accounts")

        try:
            print("Scraping accounts...")
            accounts_url = f"{self.BASE_URL}/accounts"
            await self.page.goto(accounts_url, wait_until='networkidle')
            await asyncio.sleep(2)

            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # This is a placeholder - actual selectors will depend on Simplifi's HTML structure
            # You'll need to inspect the page and update these selectors
            accounts = []

            # Example: Look for account elements (adjust selectors based on actual HTML)
            account_elements = soup.select('[data-account], .account-item, .account-row')

            for elem in account_elements:
                account = {
                    'name': elem.get_text(strip=True),
                    'id': elem.get('data-id', ''),
                    'balance': 0  # Extract from element
                }
                accounts.append(account)

            return accounts

        except Exception as e:
            print(f"Failed to retrieve accounts: {e}")
            return []

    async def get_transactions(self,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        account_id: Optional[str] = None) -> List[Dict]:
        """
        Scrape transactions from the transactions page

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            account_id: Filter by specific account

        Returns:
            List of transaction dictionaries
        """
        if not self.is_logged_in:
            raise ValueError("Must be logged in to retrieve transactions")

        try:
            await self.navigate_to_transactions()

            # Apply date filters if provided
            if start_date or end_date:
                await self._apply_date_filter(start_date, end_date)

            # Apply account filter if provided
            if account_id:
                await self._apply_account_filter(account_id)

            # Scroll to load all transactions
            print("Loading all transactions...")
            await self._scroll_to_load_all()

            # Extract transactions from page
            transactions = await self._extract_transactions_from_page()

            return transactions

        except Exception as e:
            print(f"Failed to retrieve transactions: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _apply_date_filter(self, start_date: Optional[str], end_date: Optional[str]):
        """Apply date range filter on transactions page"""
        # This will need to be customized based on Simplifi's actual UI
        print(f"Applying date filter: {start_date} to {end_date}")

        try:
            # Look for date picker elements
            # This is a placeholder - actual implementation depends on UI
            date_filter_button = 'button:has-text("Date"), .date-filter, [aria-label*="date"]'

            if await self.page.locator(date_filter_button).count() > 0:
                await self.page.click(date_filter_button)
                await asyncio.sleep(1)

                # Fill in dates (adjust selectors as needed)
                if start_date:
                    await self.page.fill('input[name="startDate"], input[placeholder*="Start"]', start_date)

                if end_date:
                    await self.page.fill('input[name="endDate"], input[placeholder*="End"]', end_date)

                # Apply filter
                await self.page.click('button:has-text("Apply"), button:has-text("Filter")')
                await asyncio.sleep(2)

        except Exception as e:
            print(f"Could not apply date filter: {e}")

    async def _apply_account_filter(self, account_id: str):
        """Apply account filter on transactions page"""
        print(f"Applying account filter: {account_id}")
        # Implementation depends on Simplifi's UI structure

    async def _scroll_to_load_all(self):
        """Scroll page to trigger lazy loading of all transactions"""
        last_height = await self.page.evaluate("document.body.scrollHeight")
        scroll_attempts = 0
        max_attempts = 20

        while scroll_attempts < max_attempts:
            # Scroll down
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # Calculate new scroll height
            new_height = await self.page.evaluate("document.body.scrollHeight")

            if new_height == last_height:
                break

            last_height = new_height
            scroll_attempts += 1

        print(f"Scrolled {scroll_attempts} times to load transactions")

    async def _extract_transactions_from_page(self) -> List[Dict]:
        """Extract transaction data from the current page"""
        print("Extracting transactions from page...")

        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')

        transactions = []

        # These selectors are placeholders - you'll need to inspect the actual Simplifi page
        # and update them to match the real HTML structure
        transaction_rows = soup.select('[data-transaction], .transaction-row, .transaction-item, tr.transaction')

        print(f"Found {len(transaction_rows)} transaction elements")

        for row in transaction_rows:
            try:
                transaction = self._parse_transaction_row(row)
                if transaction:
                    transactions.append(transaction)
            except Exception as e:
                print(f"Error parsing transaction row: {e}")
                continue

        return transactions

    def _parse_transaction_row(self, row) -> Optional[Dict]:
        """
        Parse a single transaction row

        This is a placeholder implementation - you'll need to customize
        based on the actual HTML structure of Simplifi
        """
        try:
            # Example parsing (adjust based on actual structure)
            transaction = {
                'date': '',
                'description': '',
                'amount': 0.0,
                'category': '',
                'account': '',
                'merchant': '',
                'notes': ''
            }

            # Extract date
            date_elem = row.select_one('.date, [data-date], td:nth-child(1)')
            if date_elem:
                transaction['date'] = date_elem.get_text(strip=True)

            # Extract description/merchant
            desc_elem = row.select_one('.description, .merchant, [data-description], td:nth-child(2)')
            if desc_elem:
                transaction['description'] = desc_elem.get_text(strip=True)
                transaction['merchant'] = desc_elem.get_text(strip=True)

            # Extract amount
            amount_elem = row.select_one('.amount, [data-amount], td:nth-child(3)')
            if amount_elem:
                amount_text = amount_elem.get_text(strip=True)
                # Clean up amount (remove $, commas, etc.)
                amount_text = amount_text.replace('$', '').replace(',', '').strip()
                try:
                    transaction['amount'] = float(amount_text)
                except ValueError:
                    transaction['amount'] = 0.0

            # Extract category
            category_elem = row.select_one('.category, [data-category], td:nth-child(4)')
            if category_elem:
                transaction['category'] = category_elem.get_text(strip=True)

            return transaction

        except Exception as e:
            print(f"Error parsing transaction: {e}")
            return None

    async def export_page_as_csv_from_ui(self, output_path: str = "transactions_export.csv"):
        """
        Use Simplifi's built-in export feature to download CSV

        This is often more reliable than scraping

        Args:
            output_path: Where to save the downloaded CSV
        """
        if not self.is_logged_in:
            raise ValueError("Must be logged in to export transactions")

        try:
            await self.navigate_to_transactions()

            print("Looking for export button...")

            # Look for export/download button
            export_selectors = [
                'button:has-text("Export")',
                'button:has-text("Download")',
                '[aria-label*="Export"]',
                '[aria-label*="Download"]',
                '.export-button'
            ]

            for selector in export_selectors:
                if await self.page.locator(selector).count() > 0:
                    print(f"Found export button: {selector}")

                    # Set up download handler
                    async with self.page.expect_download() as download_info:
                        await self.page.click(selector)

                    download = await download_info.value
                    await download.save_as(output_path)
                    print(f"✓ Exported transactions to {output_path}")
                    return True

            print("✗ Could not find export button")
            return False

        except Exception as e:
            print(f"Export failed: {e}")
            return False

    async def screenshot(self, filename: str = "screenshot.png"):
        """Take a screenshot of the current page (useful for debugging)"""
        if self.page:
            await self.page.screenshot(path=filename)
            print(f"Screenshot saved to {filename}")
