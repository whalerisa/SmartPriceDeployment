"""
Print Router - Handles all print-related endpoints
"""
from fastapi import APIRouter
from fastapi.responses import Response
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
import sys
import logging
import requests
import gzip
import json as json_lib

from utils.baht_text import baht_text
from config.config_external_api import LOCATION_API_URL, LOCATION_API_HEADERS

logger = logging.getLogger(__name__)

# Detect if running in frozen mode (PyInstaller)
if getattr(sys, 'frozen', False):
    if hasattr(sys, "_MEIPASS"):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# โหลด template จาก backend ตรง ๆ
env = Environment(loader=FileSystemLoader(BASE_DIR))

router = APIRouter()


@router.post("/print/quotation")
def print_quotation(payload: dict):
    """
    Generate and return a PDF quotation based on the provided payload.
    
    Args:
        payload: Dictionary containing quotation data including items, totals, and branch info
        
    Returns:
        PDF file as response
    """
    print("\n=== PRINT PAYLOAD ===")
    print(f"Sales: {payload.get('sales')}")
    print(f"SalesId: {payload.get('salesId')}")
    print(f"Employee: {payload.get('employee')}")
    
    print("\n=== PRINT PAYLOAD ITEMS ===")
    for it in payload.get("items", []):
        print(it.get("code"), it.get("unit"))

    net_total = payload.get("netTotal", 0)
    payload["amountText"] = baht_text(net_total)
    
    # ⭐ ดึงข้อมูลสาขาจาก API
    try:
        # ดึง branch code จาก payload (sales branch)
        branch_code = payload.get("branchCode", "00TR")
        
        # Normalize 90HO เป็น 00TR
        if branch_code == "90HO":
            branch_code = "00TR"
        
        print(f"🔍 Fetching branch info for: {branch_code}")
        print(f"   API URL: {LOCATION_API_URL}")
        
        data = None
        
        # ลองเรียก API ครั้งแรก (disable auto decompression)
        try:
            session = requests.Session()
            session.headers.update({"Accept-Encoding": "identity"})  # ปิด auto-decompression
            
            response = session.get(
                f"{LOCATION_API_URL}?Code={branch_code}",
                headers=LOCATION_API_HEADERS,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            print(f"✅ Successfully fetched and parsed response")
            print(f"   Response: {data}")
        except Exception as e1:
            print(f"⚠️ First attempt failed: {e1}")
            # ลองครั้งที่สอง: ใช้ urllib3 ที่ disable decompression
            try:
                import urllib3
                http = urllib3.PoolManager(decode_content=False)
                
                url = f"{LOCATION_API_URL}?Code={branch_code}"
                headers = LOCATION_API_HEADERS.copy()
                headers["Accept-Encoding"] = "identity"
                
                response = http.request("GET", url, headers=headers, timeout=10)
                content = response.data
                
                # ลองแยก decompress เอง
                if content[:2] == b'\x1f\x8b':  # gzip magic number
                    print("📦 Detected gzip compression, decompressing...")
                    content = gzip.decompress(content)
                
                data = json_lib.loads(content)
                print(f"✅ Successfully parsed response via urllib3")
                print(f"   Response: {data}")
            except Exception as e2:
                print(f"⚠️ Second attempt failed: {e2}")
                data = {}
        
        # ดึงข้อมูลสาขาจาก response
        # หมายเหตุ: API gateway D365 (silver_location_) ไม่ได้คืน field "success"
        # มันคืนมาเป็น {"data": [...]}, {"value": [...]} หรือ list ตรง ๆ
        branch_list = None
        if isinstance(data, list):
            branch_list = data
        elif isinstance(data, dict):
            branch_list = data.get("data") or data.get("value") or []

        if branch_list and len(branch_list) > 0:
            branch_info = branch_list[0]  # เอาตัวแรก
            
            print(f"📋 Branch info: {branch_info}")
            
            # ประกอบที่อยู่ตามรูปแบบ: Address+District+City+Country+Post_Code+Phone_No
            address_parts = [
                str(branch_info.get("Address", "")).strip(),
                str(branch_info.get("District", "")).strip(),
                str(branch_info.get("City", "")).strip(),
                str(branch_info.get("Country", "")).strip(),
                str(branch_info.get("Post_Code", "")).strip(),
            ]
            address_line = " ".join([p for p in address_parts if p])
            phone_no = str(branch_info.get("Phone_No", "")).strip()
            
            # เพิ่มข้อมูลสาขาไปใน payload
            payload["branchName"] = str(branch_info.get("Name", "")).strip()
            payload["branchAddress"] = address_line
            payload["branchPhone"] = phone_no
            print(f"✅ Branch info loaded: {payload['branchName']}")
            print(f"   Address: {payload['branchAddress']}")
            print(f"   Phone: {payload['branchPhone']}")
        else:
            # ถ้า API ไม่ส่งข้อมูลมา ใช้ค่า default
            print(f"⚠️ No branch data in response, using defaults")
            print(f"   Response data: {data}")
            payload["branchName"] = "บริษัท ห้างกระจกตังน้ำ จำกัด (สำนักงานใหญ่)"
            payload["branchAddress"] = "226 ถนนพระรามที่2 แขวงแสมดำ เขตบางขุนเทียน จังหวัดกรุงเทพฯ 10150"
            payload["branchPhone"] = "Tel : 0-2416-5840-1"
    except Exception as e:
        print(f"❌ Error fetching branch info: {e}")
        import traceback
        traceback.print_exc()
        # ใช้ค่า default ถ้า API ล้มเหลว
        payload["branchName"] = "บริษัท ห้างกระจกตังน้ำ จำกัด (สำนักงานใหญ่)"
        payload["branchAddress"] = "226 ถนนพระรามที่2 แขวงแสมดำ เขตบางขุนเทียน จังหวัดกรุงเทพฯ 10150"
        payload["branchPhone"] = "Tel : 0-2416-5840-1"
    
    template = env.get_template("quotation.html")

    html = template.render(q=payload)

    pdf = HTML(
        string=html,
        base_url=BASE_DIR   # ⭐ สำคัญ: ให้ WeasyPrint หา font / asset เจอ
    ).write_pdf()

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=quotation.pdf"
        }
    )
