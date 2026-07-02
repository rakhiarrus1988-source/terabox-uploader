import os
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
from config import settings
from core.credentials_manager import CredentialsManager

class TeraboxUploader:
    def __init__(self):
        self.cookies = CredentialsManager.load_terabox_cookies()
        self.driver = None
    
    def login_with_cookies(self):
        """Login to Terabox using saved cookies"""
        if not self.cookies:
            print("⚠️ No saved cookies found. Manual login required.")
            return self.manual_login()
        
        self.driver = uc.Chrome()
        self.driver.get("https://www.terabox.com/")
        
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)
        
        self.driver.refresh()
        print("✅ Logged in using saved cookies!")
        return True
    
    def manual_login(self):
        """Manual login to Terabox (opens browser)"""
        print("🌐 Opening browser for Terabox login...")
        self.driver = uc.Chrome()
        self.driver.get("https://www.terabox.com/login")
        
        input("⌨️ Please login manually in the browser, then press Enter here...")
        
        cookies = self.driver.get_cookies()
        CredentialsManager.save_terabox_cookies(cookies)
        print("✅ Cookies saved for future use!")
        return True
    
    def upload_file(self, file_path):
        """Upload file to Terabox"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None
        
        print(f"📤 Uploading to Terabox: {os.path.basename(file_path)}")
        
        # Method 1: Try using requests with cookies
        try:
            upload_url = "https://www.terabox.com/api/v1/upload"
            files = {'file': open(file_path, 'rb')}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.post(upload_url, files=files, cookies=self.cookies, headers=headers)
            
            if response.status_code == 200:
                print("✅ Upload successful!")
                return response.json()
            else:
                print(f"⚠️ Upload failed: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Upload error: {e}")
        
        # Method 2: Fallback to browser automation
        print("🔄 Trying browser automation...")
        return self.upload_with_browser(file_path)
    
    def upload_with_browser(self, file_path):
        """Upload using browser automation"""
        try:
            if not self.driver:
                self.login_with_cookies()
            
            self.driver.get("https://www.terabox.com/")
            
            upload_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Upload')]"))
            )
            upload_btn.click()
            
            file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
            file_input.send_keys(os.path.abspath(file_path))
            
            print("⏳ Upload in progress...")
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(text(), 'Complete')]"))
            )
            
            print("✅ Upload complete!")
            return True
        except Exception as e:
            print(f"❌ Browser upload failed: {e}")
            return False
    
    def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()