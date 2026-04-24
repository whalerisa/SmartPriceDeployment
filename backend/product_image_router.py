# product_image_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path
from file_storage_config import get_product_images_folder

router = APIRouter(prefix="/api/product-images", tags=["Product Images"])

# โฟลเดอร์เก็บรูปภาพสินค้า (ใช้ config)
IMAGES_DIR = Path(get_product_images_folder())
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# รองรับไฟล์ประเภทนี้
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/upload/{sku}")
async def upload_product_image(sku: str, file: UploadFile = File(...)):
    """
    อัปโหลดรูปภาพสินค้า
    - sku: รหัสสินค้า (SKU)
    - file: ไฟล์รูปภาพ
    """
    # ตรวจสอบนามสกุลไฟล์
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"ไฟล์ต้องเป็นประเภท: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # สร้างชื่อไฟล์ตาม SKU
    filename = f"{sku}{file_ext}"
    file_path = IMAGES_DIR / filename
    
    try:
        # บันทึกไฟล์
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "message": f"อัปโหลดรูปภาพสำหรับ SKU: {sku} สำเร็จ",
            "filename": filename,
            "url": f"/static/product-images/{filename}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


@router.get("/{sku}")
async def get_product_image(sku: str):
    """
    ดึงรูปภาพสินค้าตาม SKU
    - sku: รหัสสินค้า
    """
    # ค้นหาไฟล์ที่ตรงกับ SKU (ลองทุกนามสกุล)
    for ext in ALLOWED_EXTENSIONS:
        file_path = IMAGES_DIR / f"{sku}{ext}"
        if file_path.exists():
            return FileResponse(file_path)
    
    # ถ้าไม่เจอ ส่ง 404
    raise HTTPException(status_code=404, detail=f"ไม่พบรูปภาพสำหรับ SKU: {sku}")


@router.delete("/{sku}")
async def delete_product_image(sku: str):
    """
    ลบรูปภาพสินค้าตาม SKU
    - sku: รหัสสินค้า
    """
    # ค้นหาและลบไฟล์ที่ตรงกับ SKU
    deleted = False
    for ext in ALLOWED_EXTENSIONS:
        file_path = IMAGES_DIR / f"{sku}{ext}"
        if file_path.exists():
            file_path.unlink()
            deleted = True
            break
    
    if not deleted:
        raise HTTPException(status_code=404, detail=f"ไม่พบรูปภาพสำหรับ SKU: {sku}")
    
    return {
        "success": True,
        "message": f"ลบรูปภาพสำหรับ SKU: {sku} สำเร็จ"
    }


@router.get("/")
async def list_product_images():
    """
    แสดงรายการรูปภาพสินค้าทั้งหมด
    """
    images = []
    for file_path in IMAGES_DIR.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in ALLOWED_EXTENSIONS:
            sku = file_path.stem  # ชื่อไฟล์ไม่รวมนามสกุล
            images.append({
                "sku": sku,
                "filename": file_path.name,
                "url": f"/api/product-images/{sku}"
            })
    
    return {
        "total": len(images),
        "images": images
    }
