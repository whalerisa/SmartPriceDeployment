"""
File Storage Configuration

Manages folder paths for uploading project files and product images.
Provides utilities to ensure folders exist and handle file operations.
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class FileStorageConfig:
    """Singleton for file storage configuration"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def get_project_files_folder() -> str:
        """Get project files folder path"""
        folder = os.getenv("PROJECT_FILES_FOLDER", "./uploads/project_files")
        return folder
    
    @staticmethod
    def get_product_images_folder() -> str:
        """Get product images folder path"""
        folder = os.getenv("PRODUCT_IMAGES_FOLDER", "./uploads/product_images")
        return folder
    
    @staticmethod
    def ensure_folder_exists(folder_path: str) -> bool:
        """
        Ensure folder exists, create if not.
        
        Args:
            folder_path: Path to folder
            
        Returns:
            True if folder exists or was created, False if error
        """
        try:
            path = Path(folder_path)
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✅ Folder ensured: {folder_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create folder {folder_path}: {e}")
            return False
    
    @staticmethod
    def get_full_path(folder_type: str, filename: str) -> Optional[str]:
        """
        Get full file path for storage.
        
        Args:
            folder_type: "project_files" or "product_images"
            filename: Name of file to store
            
        Returns:
            Full path to file, or None if invalid folder_type
        """
        if folder_type == "project_files":
            folder = FileStorageConfig.get_project_files_folder()
        elif folder_type == "product_images":
            folder = FileStorageConfig.get_product_images_folder()
        else:
            logger.error(f"❌ Invalid folder_type: {folder_type}")
            return None
        
        # Ensure folder exists
        if not FileStorageConfig.ensure_folder_exists(folder):
            return None
        
        full_path = os.path.join(folder, filename)
        return full_path
    
    @staticmethod
    def validate_folder_path(folder_path: str) -> tuple[bool, str]:
        """
        Validate folder path.
        
        Args:
            folder_path: Path to validate
            
        Returns:
            (is_valid, message)
        """
        try:
            path = Path(folder_path)
            
            # Check if path is absolute or relative
            if not path.is_absolute():
                # Convert relative path to absolute
                path = Path.cwd() / path
            
            # Check if parent directory exists
            if not path.parent.exists():
                return False, f"Parent directory does not exist: {path.parent}"
            
            # Try to create folder
            path.mkdir(parents=True, exist_ok=True)
            
            # Check if we can write to folder
            test_file = path / ".write_test"
            try:
                test_file.touch()
                test_file.unlink()
                return True, f"Folder is valid and writable: {path}"
            except Exception as e:
                return False, f"Cannot write to folder: {e}"
        
        except Exception as e:
            return False, f"Invalid folder path: {e}"


def get_project_files_folder() -> str:
    """Get project files folder path"""
    return FileStorageConfig.get_project_files_folder()


def get_product_images_folder() -> str:
    """Get product images folder path"""
    return FileStorageConfig.get_product_images_folder()


def ensure_storage_folders_exist() -> bool:
    """
    Ensure all storage folders exist.
    Call this on application startup.
    
    Returns:
        True if all folders exist or were created, False if error
    """
    project_files_ok = FileStorageConfig.ensure_folder_exists(
        FileStorageConfig.get_project_files_folder()
    )
    product_images_ok = FileStorageConfig.ensure_folder_exists(
        FileStorageConfig.get_product_images_folder()
    )
    
    return project_files_ok and product_images_ok
