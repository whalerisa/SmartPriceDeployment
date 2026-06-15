import os
import sys
import json
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    # Add line_buffering=True so print statements appear immediately in PyInstaller frozen console
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

def convert_quote_code(input_code):
    """
    Convert quote code from format like 'TRQT' to 'TRSQ-QT'
    Rules: Take first 2 chars + 'SQ-' + last 2 chars
    """
    if len(input_code) < 4:
        print(f"[WARNING]  Warning: Input code '{input_code}' is too short. Using as-is.")
        return input_code
    
    first_two = input_code[:2]
    last_two = input_code[-2:]
    converted = f"{first_two}SQ-{last_two}"
    
    print(f"[INFO] Converting: {input_code} → {converted}")
    return converted

def execute_create_sales_quote(quote_code, rpa_data=None):
    """
    Automate creating a sales quote with specific series code
    """
    print("[START] Starting RPA script for Sales Quote creation...")
    print(f"[INFO] Quote code: {quote_code}")
    
    # Convert the quote code
    target_series = convert_quote_code(quote_code)
    
    # ⭐️ Use hardcoded localhost address since this runs locally
    chrome_address = "127.0.0.1:9222"
    
    print(f"[INFO] Connecting to Chrome at: {chrome_address}")
    
    # Chrome options to connect to existing browser
    chrome_options = Options()
    chrome_options.debugger_address = chrome_address
    
    try:
        print("🔌 Connecting to existing Chrome browser...")
        
        # For offline branch machines, we use a local bundled chromedriver.exe to prevent
        # Selenium Manager from attempting to download drivers from the internet (which fails in restricted networks).
        # We look for chromedriver.exe in the 'browser' folder relative to this running script/executable.
        if getattr(sys, 'frozen', False):
            # Running as compiled PyInstaller executable
            base_dir = os.path.dirname(sys.executable)
        else:
            # Running as standard Python script
            base_dir = os.path.dirname(os.path.abspath(__file__))

        driver_path = os.path.join(base_dir, "browser", "chromedriver.exe")
        service = None
        if os.path.exists(driver_path):
            print(f"[INFO] Found local offline driver at: {driver_path}")
            service = Service(executable_path=driver_path)
        else:
            print("[WARN] Local browser/chromedriver.exe not found! Attempting to use default Selenium Manager (requires internet)...")

        # Retry logic: Try to connect up to 5 times, waiting 2 seconds between each
        max_retries = 5
        driver = None
        last_error = None

        for attempt in range(1, max_retries + 1):
            try:
                if service:
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    driver = webdriver.Chrome(options=chrome_options)
                print(f"[OK] Connected to Chrome at {chrome_address} on attempt {attempt}")
                break
            except Exception as e:
                last_error = e
                print(f"[WAIT] Attempt {attempt}/{max_retries}: Chrome not ready yet, retrying in 2s...")
                time.sleep(2)

        if driver is None:
            print(f"[ERROR] Could not connect to Chrome after {max_retries} attempts. Last error: {last_error}")
            raise Exception("Cannot connect to Chrome. Make sure Chrome is opened with remote debugging enabled (port 9222). Please restart Chrome using 'start_agent_and_chrome.bat'.")
        
        # Get all window handles (tabs)
        windows = driver.window_handles
        print(f"[OK] Found {len(windows)} open tabs")
        
        # Search for D365 BC Sales Quotes tab
        target_window = None
        for window in windows:
            driver.switch_to.window(window)
            current_url = driver.current_url
            current_title = driver.title
            
            print(f"📄 Checking tab: {current_title[:50]}...")
            
            url_lower = current_url.lower()
            title_lower = current_title.lower()
            
            # ทาง URL: รองรับทั้ง BC online (businesscentral) และ on-premise (BCTNG / page=41)
            url_match = (
                ('businesscentral' in url_lower and 'sales' in url_lower)
                or 'bctng' in url_lower
                or 'page=41' in url_lower
            )
            # ทาง Title: รองรับทั้งเอกพจน์/พหูพจน์ และภาษาไทย
            title_match = (
                'sales quote' in title_lower
                or 'ใบเสนอราคาขาย' in current_title
            )
            
            if url_match or title_match:
                target_window = window
                print(f"[OK] Found Sales Quote tab: {current_title}")
                break
        
        if not target_window:
            print("[WARNING]  Could not find Sales Quotes tab automatically")
            print("   Using current active tab instead...")
            target_window = driver.current_window_handle
        
        driver.switch_to.window(target_window)
        print(f"[LOCATION] Current page: {driver.current_url}")
        time.sleep(1)
        
        # Get data from JSON or use defaults
        customer_no = rpa_data.get("customer_no", "00001AY") if rpa_data else "00001AY"
        sales_admin = rpa_data.get("sales_admin", "20614") if rpa_data else "20614"
        your_reference = rpa_data.get("your_reference", "TRQT-2602/0010") if rpa_data else "TRQT-2602/0010"
        
        # STEP 4: Fill in Customer No.
        print("\n" + "="*60)
        print(f"STEP 4: Filling in Customer No.: {customer_no}")
        print("="*60)
        
        js_fill_customer = f"""
        function FillCustomerNo() {{
            var customerNo = '{customer_no}';
            
            // ลองหา input ด้วย id
            var input = document.querySelector('input#b2egee');
            if (input) {{
                input.value = customerNo;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                // กด Enter
                var enterEvent = new KeyboardEvent('keydown', {{
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                }});
                input.dispatchEvent(enterEvent);
                
                return 'Filled Customer No. and pressed Enter (by id) in main document';
            }}
            
            // ลองหาด้วย aria-labelledby
            input = document.querySelector('input[aria-labelledby="b2eglbl"]');
            if (input) {{
                input.value = customerNo;
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                
                var enterEvent = new KeyboardEvent('keydown', {{
                    key: 'Enter',
                    code: 'Enter',
                    keyCode: 13,
                    which: 13,
                    bubbles: true
                }});
                input.dispatchEvent(enterEvent);
                
                return 'Filled Customer No. and pressed Enter (by aria-labelledby) in main document';
            }}
            
            // ลองหาด้วย class และ role
            var inputs = document.querySelectorAll('input.stringcontrol-edit[role="combobox"]');
            for (var i = 0; i < inputs.length; i++) {{
                if (inputs[i].maxLength === 20) {{
                    inputs[i].value = customerNo;
                    inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    var enterEvent = new KeyboardEvent('keydown', {{
                        key: 'Enter',
                        code: 'Enter',
                        keyCode: 13,
                        which: 13,
                        bubbles: true
                    }});
                    inputs[i].dispatchEvent(enterEvent);
                    
                    return 'Filled Customer No. and pressed Enter (by class) in main document';
                }}
            }}
            
            // ลองหาใน iframe
            var iframes = document.querySelectorAll('iframe');
            for (var j = 0; j < iframes.length; j++) {{
                try {{
                    var iframeDoc = iframes[j].contentDocument || iframes[j].contentWindow.document;
                    
                    input = iframeDoc.querySelector('input#b2egee');
                    if (input) {{
                        input.value = customerNo;
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        var enterEvent = new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        }});
                        input.dispatchEvent(enterEvent);
                        
                        return 'Filled Customer No. and pressed Enter (by id) in iframe ' + j;
                    }}
                    
                    input = iframeDoc.querySelector('input[aria-labelledby="b2eglbl"]');
                    if (input) {{
                        input.value = customerNo;
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        var enterEvent = new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        }});
                        input.dispatchEvent(enterEvent);
                        
                        return 'Filled Customer No. and pressed Enter (by aria-labelledby) in iframe ' + j;
                    }}
                    
                    inputs = iframeDoc.querySelectorAll('input.stringcontrol-edit[role="combobox"]');
                    for (var i = 0; i < inputs.length; i++) {{
                        if (inputs[i].maxLength === 20) {{
                            inputs[i].value = customerNo;
                            inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                            
                            var enterEvent = new KeyboardEvent('keydown', {{
                                key: 'Enter',
                                code: 'Enter',
                                keyCode: 13,
                                which: 13,
                                bubbles: true
                            }});
                            inputs[i].dispatchEvent(enterEvent);
                            
                            return 'Filled Customer No. and pressed Enter (by class) in iframe ' + j;
                        }}
                    }}
                }} catch (e) {{}}
            }}
            
            throw new Error('Customer No. input field not found');
        }}
        return FillCustomerNo();
        """
        
        try:
            result = driver.execute_script(js_fill_customer)
            print(f"[OK] {result}")
        except Exception as e:
            print(f"[ERROR] Failed to fill Customer No.: {str(e)}")
            return
        
        # Wait for page to load after entering customer
        print("[WAIT] Waiting for page to load after customer selection...")
        time.sleep(5)  # เพิ่มจาก 3 เป็น 5 วินาที
        
        # STEP 4.5: Fill in Project Code (if provided)
        project_code = rpa_data.get("project_code", "") if rpa_data else ""
        
        if project_code:
            print("\n" + "="*60)
            print(f"STEP 4.5: Filling in Project Code: {project_code}")
            print("="*60)
            
            js_fill_project_code = f"""
            function FillProjectCode() {{
                var projectCode = '{project_code}';
                console.log('=== Looking for Project No. input field ===');
                
                function tryFillInDoc(doc, location) {{
                    console.log('Searching in: ' + location);
                    
                    // วิธีที่ 1: หาด้วย controlname="Project No." (ที่แน่นอนที่สุด)
                    var containers = doc.querySelectorAll('div[controlname]');
                    for (var i = 0; i < containers.length; i++) {{
                        var controlName = containers[i].getAttribute('controlname');
                        if (controlName && controlName.trim() === 'Project No.') {{
                            console.log('Found container with controlname="Project No."');
                            var input = containers[i].querySelector('input[type="text"][maxlength="20"]');
                            if (input) {{
                                console.log('Found Project No. input by controlname, id: ' + input.id);
                                input.focus();
                                input.value = projectCode;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                
                                var enterEvent = new KeyboardEvent('keydown', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true
                                }});
                                input.dispatchEvent(enterEvent);
                                return true;
                            }}
                        }}
                    }}
                    
                    // วิธีที่ 2: หาด้วย aria-label="Choose a value for Project No."
                    var button = doc.querySelector('a[aria-label="Choose a value for Project No."]');
                    if (button) {{
                        console.log('Found button with aria-label for Project No.');
                        var ariaControls = button.getAttribute('aria-controls');
                        if (ariaControls) {{
                            var input = doc.getElementById(ariaControls);
                            if (input) {{
                                console.log('Found Project No. input by aria-controls: ' + ariaControls);
                                input.focus();
                                input.value = projectCode;
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                
                                var enterEvent = new KeyboardEvent('keydown', {{
                                    key: 'Enter',
                                    code: 'Enter',
                                    keyCode: 13,
                                    which: 13,
                                    bubbles: true
                                }});
                                input.dispatchEvent(enterEvent);
                                return true;
                            }}
                        }}
                    }}
                    
                    // วิธีที่ 3: หา label ที่มีข้อความ "Project No." แล้วหา input ที่เชื่อมโยง
                    var labels = doc.querySelectorAll('a.ms-nav-edit-control-caption');
                    for (var i = 0; i < labels.length; i++) {{
                        var text = labels[i].textContent?.trim().replace(/\\s+/g, ' ');
                        if (text === 'Project No.' || text === 'Project No') {{
                            console.log('Found Project No. label, id: ' + labels[i].id);
                            var labelId = labels[i].id;
                            if (labelId) {{
                                var input = doc.querySelector('input[aria-labelledby="' + labelId + '"]');
                                if (input && input.maxLength === 20) {{
                                    console.log('Found Project No. input by aria-labelledby: ' + labelId);
                                    input.focus();
                                    input.value = projectCode;
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    
                                    var enterEvent = new KeyboardEvent('keydown', {{
                                        key: 'Enter',
                                        code: 'Enter',
                                        keyCode: 13,
                                        which: 13,
                                        bubbles: true
                                    }});
                                    input.dispatchEvent(enterEvent);
                                    return true;
                                }}
                            }}
                        }}
                    }}
                    
                    return false;
                }}
                
                // ลองใน main document
                if (tryFillInDoc(document, 'main document')) {{
                    return 'Filled Project Code and pressed Enter in main document';
                }}
                
                // ลองหาด้วย class และ role และ maxlength="20"
                // ⭐ ต้องไม่ใช่ Customer No. field (b2egee) และต้องอยู่หลัง Customer No. field
                var inputs = document.querySelectorAll('input.stringcontrol-edit[role="combobox"]');
                var foundCustomerField = false;
                for (var i = 0; i < inputs.length; i++) {{
                    // ข้าม Customer No. field
                    if (inputs[i].id === 'b2egee') {{
                        foundCustomerField = true;
                        continue;
                    }}
                    
                    // หา field ที่อยู่หลัง Customer No. และมี maxLength = 20
                    if (foundCustomerField && inputs[i].maxLength === 20) {{
                        inputs[i].value = projectCode;
                        inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        
                        var enterEvent = new KeyboardEvent('keydown', {{
                            key: 'Enter',
                            code: 'Enter',
                            keyCode: 13,
                            which: 13,
                            bubbles: true
                        }});
                        inputs[i].dispatchEvent(enterEvent);
                        
                        return 'Filled Project Code and pressed Enter (by class) in main document, field id: ' + inputs[i].id;
                    }}
                }}
                
                // ลองใน iframe
                var iframes = document.querySelectorAll('iframe');
                for (var j = 0; j < iframes.length; j++) {{
                    try {{
                        var iframeDoc = iframes[j].contentDocument || iframes[j].contentWindow.document;
                        if (tryFillInDoc(iframeDoc, 'iframe ' + j)) {{
                            return 'Filled Project Code and pressed Enter in iframe ' + j;
                        }}
                    }} catch (e) {{
                        console.log('Error accessing iframe ' + j + ': ' + e.message);
                    }}
                }}
                
                console.log('❌ Project Code input field not found');
                return 'Project Code input field not found';
            }}
            return FillProjectCode();
            """
            
            try:
                result = driver.execute_script(js_fill_project_code)
                print(f"[OK] {result}")
                if 'not found' in result:
                    print("[WARNING]  Project Code input field not found - continuing anyway...")
                else:
                    time.sleep(2)
            except Exception as e:
                print(f"[WARNING]  Could not fill Project Code: {str(e)}")
                print("   Continuing anyway...")
        else:
            print("\n[INFO] No Project Code provided - skipping Project Code field")
        
        # STEP 5: Select Sales Admin from dropdown
        print("\n" + "="*60)
        print(f"STEP 5: Selecting Sales Admin: {sales_admin}")
        print("="*60)
        
        # Step 6.1: Type the sales admin code in the input field
        js_type_sales_admin = f"""
        function TypeSalesAdmin() {{
            var salesAdminCode = '{sales_admin}';
            console.log('=== Looking for Sales Admin input field ===');
            
            // ลองหาใน iframe ก่อน
            var iframes = document.querySelectorAll('iframe');
            console.log('Found ' + iframes.length + ' iframes');
            
            for (var j = 0; j < iframes.length; j++) {{
                try {{
                    var iframeDoc = iframes[j].contentDocument || iframes[j].contentWindow.document;
                    
                    // ลองหาด้วย aria-labelledby ที่มี "Sales Admin" ในชื่อ
                    var inputs = iframeDoc.querySelectorAll('input[role="combobox"]');
                    console.log('Found ' + inputs.length + ' combobox inputs in iframe ' + j);
                    
                    for (var i = 0; i < inputs.length; i++) {{
                        var ariaLabelledBy = inputs[i].getAttribute('aria-labelledby') || '';
                        console.log('  Input ' + i + ': aria-labelledby="' + ariaLabelledBy + '"');
                        
                        // ตรวจสอบว่า label มีคำว่า Sales Admin หรือไม่
                        if (ariaLabelledBy) {{
                            var label = iframeDoc.getElementById(ariaLabelledBy);
                            if (label && (label.textContent.includes('Sales Admin') || label.textContent.includes('พนักงานขาย'))) {{
                                console.log('Found Sales Admin input field');
                                inputs[i].focus();
                                inputs[i].value = salesAdminCode;
                                inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return 'Typed Sales Admin code in iframe ' + j;
                            }}
                        }}
                    }}
                }} catch (e) {{
                    console.log('Error accessing iframe ' + j + ': ' + e.message);
                }}
            }}
            
            // ลองหาใน main document
            var inputs = document.querySelectorAll('input[role="combobox"]');
            console.log('Found ' + inputs.length + ' combobox inputs in main document');
            
            for (var i = 0; i < inputs.length; i++) {{
                var ariaLabelledBy = inputs[i].getAttribute('aria-labelledby') || '';
                if (ariaLabelledBy) {{
                    var label = document.getElementById(ariaLabelledBy);
                    if (label && (label.textContent.includes('Sales Admin') || label.textContent.includes('พนักงานขาย'))) {{
                        console.log('Found Sales Admin input field in main document');
                        inputs[i].focus();
                        inputs[i].value = salesAdminCode;
                        inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'Typed Sales Admin code in main document';
                    }}
                }}
            }}
            
            return 'Sales Admin input field not found';
        }}
        return TypeSalesAdmin();
        """
        
        try:
            result = driver.execute_script(js_type_sales_admin)
            print(f"[OK] {result}")
            if 'not found' in result:
                print("[WARNING]  Sales Admin input field not found - continuing anyway...")
                time.sleep(2)
            else:
                # Wait for dropdown to appear
                print("[WAIT] Waiting for dropdown to appear...")
                time.sleep(2)
                
                # Step 6.2: Click the matching record in dropdown
                js_select_from_dropdown = f"""
                function SelectFromDropdown() {{
                    var targetCode = '{sales_admin}';
                    console.log('=== Looking for Sales Admin record: ' + targetCode + ' ===');
                    
                    // ลองหาใน iframe
                    var iframes = document.querySelectorAll('iframe');
                    for (var j = 0; j < iframes.length; j++) {{
                        try {{
                            var iframeDoc = iframes[j].contentDocument || iframes[j].contentWindow.document;
                            
                            // หา link ที่มี class stringcontrol-read และ text ตรงกับ targetCode
                            var links = iframeDoc.querySelectorAll('a.stringcontrol-read');
                            console.log('Iframe ' + j + ': Found ' + links.length + ' links');
                            
                            for (var i = 0; i < links.length; i++) {{
                                var text = links[i].textContent.trim();
                                if (i < 5) {{
                                    console.log('  Link ' + i + ': "' + text + '"');
                                }}
                                if (text === targetCode) {{
                                    console.log('Found matching record: ' + text);
                                    links[i].click();
                                    return 'Clicked Sales Admin record "' + targetCode + '" in iframe ' + j;
                                }}
                            }}
                        }} catch (e) {{
                            console.log('Error accessing iframe ' + j + ': ' + e.message);
                        }}
                    }}
                    
                    // ลองหาใน main document
                    var links = document.querySelectorAll('a.stringcontrol-read');
                    console.log('Main document: Found ' + links.length + ' links');
                    for (var i = 0; i < links.length; i++) {{
                        var text = links[i].textContent.trim();
                        if (text === targetCode) {{
                            console.log('Found matching record in main document: ' + text);
                            links[i].click();
                            return 'Clicked Sales Admin record "' + targetCode + '" in main document';
                        }}
                    }}
                    
                    return 'Sales Admin record "' + targetCode + '" not found in dropdown';
                }}
                return SelectFromDropdown();
                """
                
                result = driver.execute_script(js_select_from_dropdown)
                print(f"[OK] {result}")
                if 'not found' in result:
                    print("[WARNING]  Sales Admin record not found in dropdown - continuing anyway...")
        except Exception as e:
            print(f"[WARNING]  Could not select Sales Admin: {str(e)}")
            print("   Continuing anyway...")
        
        time.sleep(2)
        
        # STEP 6: Click "Show more" button in General section
        print("\n" + "="*60)
        print("STEP 6: Clicking 'Show more' button in General section")
        print("="*60)
        
        js_click_show_more = """
        function ClickShowMoreButton() {
            console.log('=== Looking for Show more button in General section ===');
            
            // ลองหาใน iframe ก่อน
            var iframes = document.querySelectorAll('iframe');
            console.log('Found ' + iframes.length + ' iframes');
            
            for (var j = 0; j < iframes.length; j++) {
                try {
                    var iframeDoc = iframes[j].contentDocument || iframes[j].contentWindow.document;
                    
                    // หา span ที่มี class ms-nav-columns-caption และมี text "General"
                    var captions = iframeDoc.querySelectorAll('span.ms-nav-columns-caption');
                    console.log('Iframe ' + j + ': Found ' + captions.length + ' captions');
                    
                    for (var i = 0; i < captions.length; i++) {
                        var captionText = captions[i].querySelector('.caption-text');
                        if (captionText && captionText.textContent.trim() === 'General') {
                            console.log('Found General caption');
                            
                            // หา parent element ของ caption
                            var parent = captions[i].parentElement;
                            if (parent) {
                                // หาปุ่ม Show more ใน parent หรือ sibling elements
                                var showMoreBtn = parent.querySelector('button.show-more-fields-button');
                                if (showMoreBtn) {
                                    console.log('Found Show more button in General section');
                                    showMoreBtn.click();
                                    return 'Clicked Show more button in General section (iframe ' + j + ')';
                                }
                                
                                // ลองหาใน next sibling
                                var nextSibling = parent.nextElementSibling;
                                if (nextSibling) {
                                    showMoreBtn = nextSibling.querySelector('button.show-more-fields-button');
                                    if (showMoreBtn) {
                                        console.log('Found Show more button in next sibling');
                                        showMoreBtn.click();
                                        return 'Clicked Show more button in General section (iframe ' + j + ')';
                                    }
                                }
                            }
                        }
                    }
                    
                    // วิธีที่ 2: หาปุ่มที่มี aria-label="General, Show more"
                    var button = iframeDoc.querySelector('button[aria-label="General, Show more"]');
                    if (button) {
                        console.log('Found Show more button by aria-label');
                        button.click();
                        return 'Clicked Show more button (by aria-label) in iframe ' + j;
                    }
                } catch (e) {
                    console.log('Error accessing iframe ' + j + ': ' + e.message);
                }
            }
            
            // ลองหาใน main document
            console.log('Searching in main document...');
            
            var captions = document.querySelectorAll('span.ms-nav-columns-caption');
            console.log('Found ' + captions.length + ' captions in main document');
            
            for (var i = 0; i < captions.length; i++) {
                var captionText = captions[i].querySelector('.caption-text');
                if (captionText && captionText.textContent.trim() === 'General') {
                    console.log('Found General caption in main document');
                    
                    var parent = captions[i].parentElement;
                    if (parent) {
                        var showMoreBtn = parent.querySelector('button.show-more-fields-button');
                        if (showMoreBtn) {
                            console.log('Found Show more button in General section');
                            showMoreBtn.click();
                            return 'Clicked Show more button in General section (main document)';
                        }
                        
                        var nextSibling = parent.nextElementSibling;
                        if (nextSibling) {
                            showMoreBtn = nextSibling.querySelector('button.show-more-fields-button');
                            if (showMoreBtn) {
                                console.log('Found Show more button in next sibling');
                                showMoreBtn.click();
                                return 'Clicked Show more button in General section (main document)';
                            }
                        }
                    }
                }
            }
            
            // วิธีที่ 2
            var button = document.querySelector('button[aria-label="General, Show more"]');
            if (button) {
                console.log('Found Show more button by aria-label in main document');
                button.click();
                return 'Clicked Show more button (by aria-label) in main document';
            }
            
            throw new Error('Show more button in General section not found');
        }
        return ClickShowMoreButton();
        """
        
        try:
            result = driver.execute_script(js_click_show_more)
            print(f"[OK] {result}")
        except Exception as e:
            print(f"[ERROR] Failed to click Show more button: {str(e)}")
            return
        
        print("[WAIT] Waiting 2 seconds for fields to expand...")
        time.sleep(2)
        
        # STEP 7: Fill in Your Reference
        print("\n" + "="*60)
        print(f"STEP 7: Filling Your Reference: {your_reference}")
        print("="*60)
        
        js_fill_your_reference = f"""
        function FillYourReference() {{
            var value = '{your_reference}';
            
            function tryFill(doc) {{
                // วิธีที่ 1: หาด้วย id (เช่น b1ksee)
                var input = doc.querySelector('input#b1ksee');
                if (input) {{
                    console.log('Found Your Reference input by id: b1ksee');
                    input.focus();
                    input.value = value;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                
                // วิธีที่ 2: หาด้วย aria-labelledby
                input = doc.querySelector('input[aria-labelledby="b1kslbl"]');
                if (input) {{
                    console.log('Found Your Reference input by aria-labelledby');
                    input.focus();
                    input.value = value;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                
                // วิธีที่ 3: หา label ที่มี text = "Your Reference" แล้วหา input ใกล้ๆ
                var labels = doc.querySelectorAll('label, span, div');
                for (var i = 0; i < labels.length; i++) {{
                    var text = labels[i].textContent?.trim();
                    if (text === "Your Reference") {{
                        console.log('Found Your Reference label');
                        
                        // หา input ที่อยู่ใกล้ label นี้
                        var parent = labels[i].closest('div');
                        if (!parent) continue;
                        
                        // ลองหาใน parent และ siblings
                        var inputs = parent.querySelectorAll('input[type="text"]');
                        for (var j = 0; j < inputs.length; j++) {{
                            if (inputs[j].maxLength === 35) {{  // Your Reference มี maxlength="35"
                                console.log('Found input with maxLength 35');
                                inputs[j].focus();
                                inputs[j].value = value;
                                inputs[j].dispatchEvent(new Event('input', {{ bubbles: true }}));
                                inputs[j].dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                        }}
                    }}
                }}
                
                return false;
            }}
            
            // ลองใน main document
            if (tryFill(document)) {{
                return "Filled Your Reference in main document";
            }}
            
            // ลองใน iframe
            var iframes = document.querySelectorAll("iframe");
            for (var i = 0; i < iframes.length; i++) {{
                try {{
                    var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                    if (tryFill(iframeDoc)) {{
                        return "Filled Your Reference in iframe " + i;
                    }}
                }} catch (e) {{
                    console.log('Error accessing iframe ' + i + ': ' + e.message);
                }}
            }}
            
            throw new Error("Your Reference field not found");
        }}
        return FillYourReference();
        """
        
        try:
            result = driver.execute_script(js_fill_your_reference)
            print(f"[OK] {result}")
        except Exception as e:
            print(f"[ERROR] Failed to fill Your Reference: {str(e)}")
            return
        
        time.sleep(2)
        
        # STEP 8-11: Add Items (Loop for multiple items)
        if rpa_data and "items" in rpa_data:
            items_to_add = rpa_data["items"]
            print("[OK] Using items from API data")
        else:
            items_to_add = []
        
        print("\n" + "="*60)
        print(f"STEP 8-11: Adding {len(items_to_add)} items")
        print("="*60)
        
        # JavaScript to switch to iframe
        js_switch_to_iframe = """
        function SwitchToFormIframe() {
            var iframes = document.querySelectorAll('iframe');
            for (var i = 0; i < iframes.length; i++) {
                try {
                    var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                    var lookupBtn = iframeDoc.querySelector('a[aria-label="Choose a value for No."]');
                    if (lookupBtn) {
                        return i;
                    }
                } catch (e) {}
            }
            return -1;
        }
        return SwitchToFormIframe();
        """
        
        for item_index, item in enumerate(items_to_add, 1):
            print("\n" + "-"*60)
            print(f"Processing Item {item_index}/{len(items_to_add)}: {item.get('item_code', '')}")
            print("-"*60)
            
            item_code = item.get('item_code', '')
            description_text = item.get('description', '')
            quantity = item.get('quantity', '1')
            is_glass_item = item_code.upper().startswith('G')
            
            # STEP 8: Add Item Code
            print(f"\n[Item {item_index}] Step 8: Adding Item Code: {item_code}")
            
            js_add_item = f"""
            function AddItem() {{
                var itemCode = '{item_code}';
                
                function tryAdd(doc) {{
                    var lookupBtn = doc.querySelector('a[aria-label="Choose a value for No."]');
                    if (!lookupBtn) return false;
                    
                    var inputId = lookupBtn.getAttribute('aria-controls');
                    if (!inputId) return false;
                    
                    var input = doc.getElementById(inputId);
                    if (!input) return false;
                    
                    input.focus();
                    input.value = itemCode;
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    
                    return true;
                }}
                
                if (tryAdd(document)) {{
                    return "Item added in main document";
                }}
                
                var iframes = document.querySelectorAll('iframe');
                for (var i = 0; i < iframes.length; i++) {{
                    try {{
                        var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                        if (tryAdd(iframeDoc)) {{
                            return "Item added in iframe " + i;
                        }}
                    }} catch (e) {{}}
                }}
                
                throw new Error("Item No. field not found");
            }}
            return AddItem();
            """
            
            try:
                result = driver.execute_script(js_add_item)
                print(f"[OK] {result}")
            except Exception as e:
                print(f"[ERROR] Failed to add item: {str(e)}")
                continue
            
            print("[WAIT] Waiting 1 seconds after adding item...")
            time.sleep(1)
            
            # STEP 9: Fill Description
            print(f"\n[Item {item_index}] Step 9: Filling Description: {description_text}")
            
            try:
                iframe_index = driver.execute_script(js_switch_to_iframe)
                if iframe_index >= 0:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframes[iframe_index])
                
                actions = ActionChains(driver)
                
                if item_index == 1:
                    print("[WAIT] First item - waiting 1 seconds for auto-description...")
                    time.sleep(2)
                
                print("[WAIT] Pressing Tab 1 time...")
                actions.send_keys(Keys.TAB).perform()
                time.sleep(1)
                
                print("[WAIT] Pressing Tab 3 more times...")
                for i in range(3):
                    actions.send_keys(Keys.TAB).perform()
                    time.sleep(0.5)
                
                print("[WAIT] Waiting 1 seconds...")
                time.sleep(1)
                
                print("[WAIT] Selecting all text (Ctrl+A)...")
                actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
                
                print("[WAIT] Deleting selected text...")
                actions.send_keys(Keys.DELETE).perform()
                time.sleep(0.5)
                
                print(f"[WAIT] Typing new description: {description_text}")
                actions.send_keys(description_text).perform()
                
                driver.switch_to.default_content()
                print(f"[OK] Description filled successfully")
                
            except Exception as e:
                print(f"[ERROR] Failed to fill Description: {str(e)}")
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                continue
            
            time.sleep(2)
            
            # STEP 10: Fill Quantity
            print(f"\n[Item {item_index}] Step 10: Filling Quantity: {quantity}")
            
            try:
                iframe_index = driver.execute_script(js_switch_to_iframe)
                if iframe_index >= 0:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframes[iframe_index])
                
                actions = ActionChains(driver)
                
                if item_index == 1:
                    print("[WAIT] First item - waiting 3 seconds for system to load Bin Code and other fields...")
                    time.sleep(3)
                else:
                    time.sleep(1)
 
                print("[WAIT] Pressing Tab 3 times...")
                for i in range(3):
                    actions.send_keys(Keys.TAB).perform()
                    time.sleep(1)
                
                if item_index == 1:
                    print("[CHECK] Checking if focused on Quantity field...")
                    
                    js_check_quantity = """
                    function CheckQuantityFocus() {
                        var activeElement = document.activeElement;
                        
                        var parentTd = activeElement.closest('td[controlname="Quantity"]');
                        if (parentTd) {
                            return true;
                        }
                        
                        var iframes = document.querySelectorAll('iframe');
                        for (var i = 0; i < iframes.length; i++) {
                            try {
                                var iframeDoc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                                activeElement = iframeDoc.activeElement;
                                parentTd = activeElement.closest('td[controlname="Quantity"]');
                                if (parentTd) {
                                    return true;
                                }
                            } catch (e) {}
                        }
                        
                        return false;
                    }
                    return CheckQuantityFocus();
                    """
                    
                    driver.switch_to.default_content()
                    is_on_quantity = driver.execute_script(js_check_quantity)
                    
                    if iframe_index >= 0:
                        iframes = driver.find_elements(By.TAG_NAME, "iframe")
                        driver.switch_to.frame(iframes[iframe_index])
                    
                    if not is_on_quantity:
                        print("[WAIT] Not on Quantity field, pressing Tab 1 more time...")
                        actions.send_keys(Keys.TAB).perform()
                        time.sleep(1)
                    else:
                        print("[OK] Already on Quantity field")
                
                print(f"[WAIT] Typing quantity: {quantity}")
                actions.send_keys(quantity).perform()
                
                driver.switch_to.default_content()
                print(f"[OK] Quantity filled successfully")
                
            except Exception as e:
                print(f"[ERROR] Failed to fill Quantity: {str(e)}")
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                continue
            
            time.sleep(2)
            
            # STEP 11: Fill Price
            print(f"\n[Item {item_index}] Step 11: Filling price")
            
            try:
                iframe_index = driver.execute_script(js_switch_to_iframe)
                if iframe_index >= 0:
                    iframes = driver.find_elements(By.TAG_NAME, "iframe")
                    driver.switch_to.frame(iframes[iframe_index])
                
                actions = ActionChains(driver)
                
                if is_glass_item:
                    print("[WAIT] Item starts with 'G' - filling glass prices...")
                    
                    print("[WAIT] Pressing Tab 2 times to reach price per sq.ft...")
                    for i in range(2):
                        actions.send_keys(Keys.TAB).perform()
                        time.sleep(0.5)
                    
                    price_per_sqft = item.get('price_per_sqft', '24')
                    print(f"[WAIT] Typing price per sq.ft: {price_per_sqft}")
                    actions.send_keys(price_per_sqft).perform()
                    time.sleep(0.5)
                    
                    print("[WAIT] Pressing Tab 1 time to reach price per sheet...")
                    actions.send_keys(Keys.TAB).perform()
                    time.sleep(0.5)
                    
                    price_per_sheet = item.get('price_per_sheet', '300')
                    print(f"[WAIT] Typing price per sheet: {price_per_sheet}")
                    actions.send_keys(price_per_sheet).perform()
                    
                    print(f"[OK] Glass prices filled: {price_per_sqft} baht/sq.ft, {price_per_sheet} baht/sheet")
                    
                else:
                    print("[WAIT] Item does not start with 'G' - filling unit price...")
                    
                    print("[WAIT] Pressing Tab 3 times to reach unit price...")
                    for i in range(3):
                        actions.send_keys(Keys.TAB).perform()
                        time.sleep(0.5)
                    
                    unit_price = item.get('unit_price', '500')
                    print(f"[WAIT] Typing unit price: {unit_price}")
                    actions.send_keys(unit_price).perform()
                    
                    print(f"[OK] Unit price filled: {unit_price} baht")
                
                driver.switch_to.default_content()
                
            except Exception as e:
                print(f"[ERROR] Failed to fill price: {str(e)}")
                try:
                    driver.switch_to.default_content()
                except:
                    pass
                continue
            
            time.sleep(2)
            
            if item_index < len(items_to_add):
                print(f"\n[Item {item_index}] Moving to next line...")
                
                try:
                    iframe_index = driver.execute_script(js_switch_to_iframe)
                    if iframe_index >= 0:
                        iframes = driver.find_elements(By.TAG_NAME, "iframe")
                        driver.switch_to.frame(iframes[iframe_index])
                    
                    actions = ActionChains(driver)
                    
                    print("[WAIT] Pressing Tab 7 times to go to next line...")
                    for i in range(7):
                        actions.send_keys(Keys.TAB).perform()
                        time.sleep(0.5)
                    
                    driver.switch_to.default_content()
                    print(f"[OK] Moved to next line")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to move to next line: {str(e)}")
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass
                
                time.sleep(2)
            actions.send_keys(Keys.TAB).perform()
            time.sleep(0.5)
        
        print("\n" + "="*60)
        print(f"[OK] All {len(items_to_add)} items added successfully!")
        print("="*60)
        time.sleep(2)
        print("\n" + "="*60)
        print("[OK] RPA script completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"[ERROR] Error occurred: {str(e)}")
        print("\n[TIP] Make sure Chrome is running with remote debugging.")
        raise

class RPAHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        # Handle CORS and Private Network Access (PNA) preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/rpa/create-quote":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Private-Network', 'true')
            self.end_headers()

            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                request_data = json.loads(post_data.decode('utf-8'))

                print("\n" + "="*60)
                print("LOCAL RPA REQUEST RECEIVED")
                print(f"Quote Code: {request_data.get('quote_code', '')}")
                print(f"Customer: {request_data.get('customer_no', '')}")
                print(f"Project Code: {request_data.get('project_code', '')}")  # ⭐ เพิ่ม debug
                print(f"Items Count: {len(request_data.get('items', []))}")
                print("="*60 + "\n")

                rpa_data = {
                    "quote_code": request_data.get('quote_code', ''),
                    "customer_no": request_data.get('customer_no', ''),
                    "sales_admin": request_data.get('sales_admin', ''),
                    "your_reference": request_data.get('your_reference', ''),
                    "project_code": request_data.get('project_code', ''),
                    "items": [
                        {
                            "item_code": item.get('sku', ''),
                            "description": item.get('description', ''),
                            "quantity": item.get('quantity', ''),
                            "unit_price": item.get('unit_price', ''),
                            "price_per_sqft": item.get('price_per_sqft', ''),
                            "price_per_sheet": item.get('price_per_sheet', ''),
                        }
                        for item in request_data.get('items', [])
                    ],
                }
                
                # ⭐ Debug: แสดง project_code ที่ได้รับ
                print(f"\n🔍 [RPA DEBUG] Project Code received: '{rpa_data.get('project_code', '')}'")
                if not rpa_data.get('project_code'):
                    print("⚠️ [RPA WARNING] No project_code in request!")
                print()

                execute_create_sales_quote(request_data.get('quote_code', ''), rpa_data)

                response = {
                    "success": True,
                    "message": "Local RPA executed successfully",
                    "output": "Sales Quote created in D365 BC"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                error_msg = str(e)
                print(f"[ERROR] Failed to execute RPA: {error_msg}")
                response = {
                    "success": False,
                    "message": f"Failed to execute RPA script: {error_msg}"
                }
                self.wfile.write(json.dumps(response).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

def run_server(port=8001):
    print("="*60)
    print("   SMART PRICING LOCAL RPA AGENT IS STARTING...")
    print("="*60)
    print("Initializing server...")

    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, RPAHandler)

    print(f"\n[OK] Local RPA Agent is running and listening on port {port}!")
    print("[INFO] Waiting for requests from the Smart Pricing Web App...")
    print("[INFO] (Do not close this window while working)\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == "__main__":
    run_server()
