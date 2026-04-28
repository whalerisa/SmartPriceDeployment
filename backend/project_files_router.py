# project_files_router.py
"""
Project Files Router - Upload only

Manages uploading project files.
Uses configurable folder path from file_storage_config.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
from pathlib import Path
from datetime import datetime
from file_storage_config import get_project_files_folder
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/project-files", tags=["Project Files"])

# โฟลเดอร์เก็บไฟล์โครงการ (ใช้ config)
FILES_DIR = Path(get_project_files_folder())
FILES_DIR.mkdir(parents=True, exist_ok=True)

logger.info(f"✅ Project files folder initialized: {FILES_DIR}")
logger.info(f"   Absolute path: {FILES_DIR.absolute()}")
logger.info(f"   Exists: {FILES_DIR.exists()}")
logger.info(f"   Is writable: {os.access(FILES_DIR, os.W_OK)}")

# รองรับไฟล์ประเภทนี้
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".txt", ".jpg", ".jpeg", ".png"}


@router.post("/upload/{project_code}")
async def upload_project_file(project_code: str, file: UploadFile = File(...)):
    """
    อัปโหลดไฟล์โครงการ
    
    Args:
        project_code: รหัสโครงการ (เช่น PJ6904016)
        file: ไฟล์ที่ต้องการอัปโหลด
    
    Returns:
        {"success": bool, "message": str, "file_path": str}
    """
    logger.info(f"📁 Uploading file for project: {project_code}")
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
    
    # สร้างโฟลเดอร์สำหรับโครงการ (ตามรหัสโครงการ)
    project_dir = FILES_DIR / project_code
    project_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"   Project directory: {project_dir}")
    logger.info(f"   Absolute path: {project_dir.absolute()}")
    logger.info(f"   Exists: {project_dir.exists()}")
    logger.info(f"   Is writable: {os.access(project_dir, os.W_OK)}")
    
    # ใช้ชื่อไฟล์เดิม
    filename = file.filename
    file_path = project_dir / filename
    
    logger.info(f"   Saving as: {filename}")
    logger.info(f"   Full path: {file_path}")
    
    try:
        # บันทึกไฟล์
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"✅ File uploaded successfully")
        logger.info(f"   File size: {file_path.stat().st_size} bytes")
        
        return {
            "success": True,
            "message": f"อัปโหลดไฟล์สำหรับโครงการ {project_code} สำเร็จ",
            "file_path": str(file_path),
            "relative_path": str(file_path.relative_to(FILES_DIR.parent) if FILES_DIR.parent in file_path.parents else file_path)
        }
    except Exception as e:
        logger.error(f"❌ Error uploading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")
