# project_files_router.py
"""
Project Files Router

Manages uploading and downloading project files.
Uses configurable folder path from file_storage_config.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
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
        {
            "success": bool,
            "message": str,
            "filename": str,
            "url": str,
            "size": int,
            "uploaded_at": str
        }
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
        
        # ดึงขนาดไฟล์
        file_size = file_path.stat().st_size
        
        return {
            "success": True,
            "message": f"อัปโหลดไฟล์สำหรับโครงการ {project_id} สำเร็จ",
            "filename": filename,
            "url": f"/api/project-files/download/{project_id}/{filename}",
            "size": file_size,
            "uploaded_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


@router.get("/download/{project_id}/{filename}")
async def download_project_file(project_id: str, filename: str):
    """
    ดาวน์โหลดไฟล์โครงการ
    
    Args:
        project_id: รหัสโครงการ
        filename: ชื่อไฟล์
    """
    file_path = FILES_DIR / project_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {filename}")
    
    return FileResponse(file_path, filename=filename)


@router.get("/list/{project_id}")
async def list_project_files(project_id: str):
    """
    แสดงรายการไฟล์โครงการ
    
    Args:
        project_id: รหัสโครงการ
    
    Returns:
        {
            "project_id": str,
            "total": int,
            "files": [
                {
                    "filename": str,
                    "size": int,
                    "uploaded_at": str,
                    "url": str
                }
            ]
        }
    """
    project_dir = FILES_DIR / project_id
    
    if not project_dir.exists():
        return {
            "project_id": project_id,
            "total": 0,
            "files": []
        }
    
    files = []
    for file_path in project_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            files.append({
                "filename": file_path.name,
                "size": stat.st_size,
                "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "url": f"/api/project-files/download/{project_id}/{file_path.name}"
            })
    
    # เรียงลำดับตามวันที่อัปโหลด (ใหม่สุดก่อน)
    files.sort(key=lambda x: x["uploaded_at"], reverse=True)
    
    return {
        "project_id": project_id,
        "total": len(files),
        "files": files
    }


@router.delete("/delete/{project_id}/{filename}")
async def delete_project_file(project_id: str, filename: str):
    """
    ลบไฟล์โครงการ
    
    Args:
        project_id: รหัสโครงการ
        filename: ชื่อไฟล์
    """
    file_path = FILES_DIR / project_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์: {filename}")
    
    try:
        file_path.unlink()
        return {
            "success": True,
            "message": f"ลบไฟล์ {filename} สำเร็จ"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")


@router.delete("/delete-all/{project_id}")
async def delete_all_project_files(project_id: str):
    """
    ลบไฟล์โครงการทั้งหมด
    
    Args:
        project_id: รหัสโครงการ
    """
    project_dir = FILES_DIR / project_id
    
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบโครงการ: {project_id}")
    
    try:
        shutil.rmtree(project_dir)
        return {
            "success": True,
            "message": f"ลบไฟล์โครงการ {project_id} ทั้งหมดสำเร็จ"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาด: {str(e)}")
