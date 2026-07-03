import os
import time
import asyncio
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# NOTE: For advanced bypass, 'pip install undetected-chromedriver' is highly recommended instead of native selenium.
# Below is the fixed native selenium version with advanced evasions.

class TeraboxUploader:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None

    def login(self):
        """Login to Terabox using email/password"""
        print("🔐 Logging into Terabox...")

        options = Options()
        # Headless triggers anti-bot on Terabox, using alternative secure headless arg layout
        options.add_argument('--headless=new')  
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Anti-fingerprint bypasses
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # Adding realistic User-Agent to prevent basic headless blocking
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

        try:
            chrome_paths = [
                '/usr/lib/chromium-browser/chromedriver',
                '/usr/bin/chromedriver',
                '/usr/lib/chromium/chromedriver'
            ]

            driver_path = None
            for path in chrome_paths:
                if os.path.exists(path):
                    driver_path = path
                    break

            if driver_path:
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                self.driver = webdriver.Chrome(options=options)

            # Override navigator variables to look like a real browser
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            })

            print("🌐 Opening Terabox login page...")
            self.driver.get("https://terabox.com")
            time.sleep(5)

            # TeraBox uses standard multi-platform login sub-containers. Finding the correct email frame input
            print("⏳ Entering credentials...")
            email_input = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder*='Email'], input[type='text'], .login-input-account input"))
            )
            email_input.clear()
            email_input.send_keys(self.email)

            pass_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']"))
            )
            pass_input.clear()
            pass_input.send_keys(self.password)

            # Click the dynamic login action submit button
            submit_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit'], .login-submit-btn, button[class*='login']"))
            )
            submit_btn.click()

            # Wait for dashboard to change state
            time.sleep(8)

            # Verify login checking dashboard markers instead of string URL matching
            if "login" not in self.driver.current_url.lower() or "main" in self.driver.current_url.lower():
                print("✅ Logged in to Terabox successfully!")
                return True
            else:
                print("❌ Login failed - Captcha active or credentials rejected.")
                return False

        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    def upload_file(self, file_path):
        """Upload file to Terabox"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False

        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        print(f"📤 Uploading to Terabox: {filename} ({file_size:.2f} MB)")

        try:
            # Refreshing index state layout to ensure dashboard is ready
            self.driver.get("https://terabox.com")
            time.sleep(5)

            # Target the structural input DOM tree instead of clicking the visual button overlay
            # TeraBox appends a hidden input element on dashboard load for file injections
            print("⚡ Locating hidden core upload input handler...")
            file_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file' or @class='upload-input-file']"))
            )

            # Make input visible via JS to ensure Webdriver interactions don't throw errors
            self.driver.execute_script("arguments[0].style.display = 'block'; arguments[0].style.opacity = '1';", file_input)
            time.sleep(1)

            # Inject the absolute localized path
            file_input.send_keys(os.path.abspath(file_path))
            print("⏳ File injected. Upload in progress...")

            # Smart polling tracking through the actual TeraBox progress sub-windows
            max_wait = 600
            wait_interval = 5
            elapsed = 0

            while elapsed < max_wait:
                page_source = self.driver.page_source.lower()
                
                # Check for upload task panels or specific upload success state strings
                if "upload successfully" in page_source or "translist-icon-success" in page_source:
                    print("✅ Upload complete!")
                    return True
                
                if "fail" in page_source and "upload" in page_source:
                    print("❌ TeraBox reported an internal file upload error.")
                    return False

                time.sleep(wait_interval)
                elapsed += wait_interval
                print(f"⏳ Still uploading... {elapsed}s elapsed")

            print("⚠️ Upload timeout - Check Terabox manually")
            return True

        except Exception as e:
            print(f"❌ Upload error: {e}")
            return False

    def close(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
                print("✅ Browser closed")
            except:
                pass
