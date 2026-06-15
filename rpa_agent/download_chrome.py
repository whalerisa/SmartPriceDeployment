import os
import sys
import json
import time
import urllib.request
import zipfile
import shutil
import ssl
import subprocess

# Bypass SSL verification if needed for corporate networks
ssl._create_default_https_context = ssl._create_unverified_context

# Target platform for 32-bit Windows
PLATFORM = "win32"
# Google Chrome for Testing JSON API
API_URL = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"

BROWSER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "browser")

def download_file(url, dest_path):
    print(f"Downloading {url}...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
        shutil.copyfileobj(response, out_file)

def extract_zip(zip_path, extract_to):
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def kill_chrome_processes():
    """Kill any leftover Chrome for Testing / chromedriver processes that may
    lock files in the browser directory (common cause of WinError 5)."""
    if os.name != "nt":
        return
    for proc in ("chrome.exe", "chromedriver.exe"):
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", proc, "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass

def move_with_retry(src, dst, retries=10, delay=1.0):
    """Move src -> dst, retrying on PermissionError.

    On Windows the freshly extracted files are often briefly locked by
    antivirus / Defender, which makes the first rename fail with WinError 5.
    Retrying after a short delay almost always succeeds."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            if os.path.exists(dst):
                shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
            shutil.move(src, dst)
            return
        except PermissionError as e:
            last_err = e
            print(f"   [retry {attempt}/{retries}] locked, waiting {delay}s... ({e})")
            time.sleep(delay)
    raise last_err

def main():
    print("Fetching latest stable Chrome for Testing versions...")

    req = urllib.request.Request(API_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))

    stable_channel = data["channels"]["Stable"]
    version = stable_channel["version"]
    print(f"Latest stable version: {version}")

    # Find downloads for the target platform
    chrome_url = None
    chromedriver_url = None

    for download in stable_channel["downloads"]["chrome"]:
        if download["platform"] == PLATFORM:
            chrome_url = download["url"]
            break

    for download in stable_channel["downloads"]["chromedriver"]:
        if download["platform"] == PLATFORM:
            chromedriver_url = download["url"]
            break

    if not chrome_url or not chromedriver_url:
        print(f"ERROR: Could not find downloads for platform {PLATFORM}")
        sys.exit(1)

    print(f"Found Chrome URL: {chrome_url}")
    print(f"Found ChromeDriver URL: {chromedriver_url}")

    # Kill any leftover Chrome/ChromeDriver processes that could lock files
    kill_chrome_processes()

    # Create clean browser directory
    if os.path.exists(BROWSER_DIR):
        print("Cleaning up existing browser directory...")
        shutil.rmtree(BROWSER_DIR, ignore_errors=True)
    os.makedirs(BROWSER_DIR)

    # Download and extract Chrome
    chrome_zip = os.path.join(BROWSER_DIR, "chrome.zip")
    download_file(chrome_url, chrome_zip)
    extract_zip(chrome_zip, BROWSER_DIR)
    os.remove(chrome_zip)

    # Download and extract ChromeDriver
    chromedriver_zip = os.path.join(BROWSER_DIR, "chromedriver.zip")
    download_file(chromedriver_url, chromedriver_zip)
    extract_zip(chromedriver_zip, BROWSER_DIR)
    os.remove(chromedriver_zip)

    # Move files to root of browser directory for easier access
    chrome_extracted_dir = os.path.join(BROWSER_DIR, f"chrome-{PLATFORM}")
    chromedriver_extracted_dir = os.path.join(BROWSER_DIR, f"chromedriver-{PLATFORM}")

    # Rename chrome-win32 to chrome (with retry to survive AV/file locks)
    final_chrome_dir = os.path.join(BROWSER_DIR, "chrome")
    move_with_retry(chrome_extracted_dir, final_chrome_dir)

    # Move chromedriver.exe out of chromedriver-win32 to browser/chromedriver.exe
    chromedriver_exe = os.path.join(chromedriver_extracted_dir, "chromedriver.exe")
    move_with_retry(chromedriver_exe, os.path.join(BROWSER_DIR, "chromedriver.exe"))

    # Clean up empty chromedriver folder
    shutil.rmtree(chromedriver_extracted_dir, ignore_errors=True)

    print(f"\nSUCCESS: Chrome for Testing and ChromeDriver ({version}) downloaded successfully to:")
    print(BROWSER_DIR)

if __name__ == "__main__":
    main()
