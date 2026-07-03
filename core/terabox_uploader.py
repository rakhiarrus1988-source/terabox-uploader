import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

class TeraboxUploader:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.driver = None
    
    def login(self):
        """Login to Terabox using email/password"""
        print("🔐 Logging into Terabox...")
        
        # Chrome options for Colab
        options = Options()
        options.add_argument('--headless=new')  # Headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Colab mein ChromeDriver ka path
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
                # Auto-detect
                self.driver = webdriver.Chrome(options=options)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("🌐 Opening Terabox login page...")
            self.driver.get("https://www.terabox.com/")
            time.sleep(3)
            
            # Click login button first (if visible)
            try:
                login_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Login')]"))
                )
                login_btn.click()
                time.sleep(2)
            except:
                pass
            
            # Find email/username field
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='email' or @name='email' or contains(@placeholder, 'email') or contains(@placeholder, 'Email')]"))
            )
            email_input.clear()
            email_input.send_keys(self.email)
            
            # Find password field
            pass_input = self.driver.find_element(By.XPATH, "//input[@type='password']")
            pass_input.clear()
            pass_input.send_keys(self.password)
            
            # Click login/submit button
            submit_btn = self.driver.find_element(By.XPATH, "//button[@type='submit' or contains(text(), 'Login') or contains(text(), 'Sign in')]")
            submit_btn.click()
            
            time.sleep(5)
            
            # Check if login successful
            if "login" not in self.driver.current_url.lower():
                print("✅ Logged in to Terabox successfully!")
                return True
            else:
                print("❌ Login failed - Still on login page")
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
            # Go to homepage
            self.driver.get("https://www.terabox.com/")
            time.sleep(3)
            
            # Find and click upload button
            upload_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Upload')]"))
            )
            upload_btn.click()
            time.sleep(2)
            
            # Find file input element
            file_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            
            # Send file path
            file_input.send_keys(os.path.abspath(file_path))
            
            print("⏳ Upload in progress... This may take a while.")
            
            # Wait for upload to complete (max 10 minutes)
            max_wait = 600
            wait_interval = 10
            elapsed = 0
            
            while elapsed < max_wait:
                try:
                    page_source = self.driver.page_source.lower()
                    if "complete" in page_source or "success" in page_source or "done" in page_source:
                        print("✅ Upload complete!")
                        return True
                except:
                    pass
                
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