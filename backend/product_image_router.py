# product_image_router.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
import shutil
from pathlib import Path
from file_storage_config import get_product_images_folder
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/product-images", tags=["Product Images"])

# โฟลเดอร์เก็บรูปภาพสินค้า (ใช้ config)
IMAGES_DIR = Path(get_product_images_folder())
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"✅ Product images folder initialized: {IMAGES_DIR}")
logger.info(f"   Absolute path: {IMAGES_DIR.absolute()}")
logger.info(f"   Exists: {IMAGES_DIR.exists()}")
logger.info(f"   Is writable: {os.access(IMAGES_DIR, os.W_OK)}")

# รองรับไฟล์ประเภทนี้
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# ขนาดไฟล์สูงสุด: 1 MB
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB in bytes


@router.post("/upload/{sku}")
async def upload_product_image(sku: str, file: UploadFile = File(...)):
    """
    อัปโหลดรูปภาพสินค้า
    - sku: รหัสสินค้า (SKU)
    - file: ไฟล์รูปภาพ (ขนาดไม่เกิน 1 MB)
    """
    logger.info(f"🖼️ Uploading image for SKU: {sku}")
    logger.info(f"   Filename: {file.filename}")
    logger.info(f"   Content-Type: {file.content_type}")
    
    # ตรวจสอบนามสกุลไฟล์
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"❌ Invalid file extension: {file_ext}")
        raise HTTPException(
            status_code=400,
            detail=f"ไฟล์ต้องเป็นประเภท: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # ตรวจสอบขนาดไฟล์
    # อ่านเนื้อหาไฟล์เพื่อตรวจสอบขนาด
    file_content = await file.read()
    file_size = len(file_content)
    
    if file_size > MAX_FILE_SIZE:
        file_size_mb = file_size / (1024 * 1024)
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        logger.warning(f"❌ File size exceeds limit: {file_size_mb:.2f} MB > {max_size_mb:.2f} MB")
        raise HTTPException(
            status_code=413,
            detail=f"ขนาดไฟล์เกินขีดจำกัด ({file_size_mb:.2f} MB > {max_size_mb:.2f} MB)"
        )
    
    # Reset file pointer หลังจากอ่านเนื้อหา
    await file.seek(0)
    # สร้างชื่อไฟล์ตาม SKU
    filename = f"{sku}{file_ext}"
    file_path = IMAGES_DIR / filename
    
    logger.info(f"   Saving as: {filename}")
    logger.info(f"   Full path: {file_path}")
    logger.info(f"   File size: {file_size / (1024 * 1024):.2f} MB")
    
    try:
        # บันทึกไฟล์โดยใช้เนื้อหาที่อ่านมาแล้ว
        with file_path.open("wb") as buffer:
            buffer.write(file_content)
        
        logger.info(f"✅ Image uploaded successfully")
        logger.info(f"   File size: {file_path.stat().st_size} bytes")
        
        return {
            "success": True,
            "message": f"อัปโหลดรูปภาพสำหรับ SKU: {sku} สำเร็จ",
            "filename": filename,
            "url": f"/static/product-images/{filename}",
            "file_path": str(file_path),
            "file_size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
        }
    except Exception as e:
        logger.error(f"❌ Error uploading image: {str(e)}", exc_info=True)
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
            logger.info(f"📁 Found image for SKU {sku}: {file_path}")
            return FileResponse(file_path)
    
    # ถ้าไม่เจอ ส่ง 404
    logger.warning(f"⚠️ Image not found for SKU: {sku}")
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
            logger.info(f"🗑️ Deleted image for SKU {sku}: {file_path}")
            deleted = True
            break
    
    if not deleted:
        logger.warning(f"⚠️ Image not found for SKU: {sku}")
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
    
    logger.info(f"📊 Listed {len(images)} product images")
    return {
        "total": len(images),
        "images": images
    }
