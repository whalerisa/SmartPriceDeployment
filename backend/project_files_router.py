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

router = APIRouter(prefix="/api/project-files", tags=["Project Files"])

# โฟลเดอร์เก็บไฟล์โครงการ (ใช้ config)
FILES_DIR = Path(get_project_files_folder())
FILES_DIR.mkdir(parents=True, exist_ok=True)

# รองรับไฟล์ประเภทนี้
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".txt", ".jpg", ".jpeg", ".png"}


@router.post("/upload/{project_id}")
async def upload_project_file(project_id: str, file: UploadFile = File(...)):
    """
    อัปโหลดไฟล์โครงการ
    
    Args:
        project_id: รหัสโครงการ
        file: ไฟล์ที่ต้องการอัปโหลด
    
    Returns:
        {"success": bool, "message": str}
    """
    # ตรวจสอบนามสกุลไฟล์
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"ไฟล์ต้องเป็นประเภท: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # สร้างโฟลเดอร์สำหรับโครงการ
    project_dir = FILES_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # สร้างชื่อไฟล์ที่ไม่ซ้ำ (เพิ่ม timestamp)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    file_path = project_dir / filename
    
    try:
        # บันทึกไฟล์
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "message": f"อัปโหลดไฟล์สำหรับโครงการ {project_id} สำเร็จ"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")
