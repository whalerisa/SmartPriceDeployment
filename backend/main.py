# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from customer import router as customer_router   
from items import router as items_router
from employees import router as employees_router
from login import router as login_router
from pricing_router import router as pricing_router
from shipping import router as shipping_router
from quotation import router as quotation_router
from cross_sell_router import cross_sell_router
from invoice_router import router as invoice_router
from price_update import router as price_update_router
from customer_analytics import router as customer_analytics_router
from api.router_sq import router as sq_router
from products_router import api_router
from cache_refresh_router import router as cache_refresh_router
from admin_router import router as admin_router
from config_router import router as config_router
from branch import router as branch_router
from credit_router import router as credit_router
from chrome_debug_router import router as chrome_debug_router
from promotion_router import router as promotion_router
from project_price_router import router as project_price_router
from special_price_request_router import router as special_price_request_router
from print_router import router as print_router
from product_image_router import router as product_image_router
from project_files_router import router as project_files_router
from statistics_router import router as statistics_router


from config.config_external_api import CUSTOMER_API_KEY
# from logging_config import setup_logging

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
import sys
import logging

# Set up logging configuration
# setup_logging(log_dir="logs", log_level="INFO")
logger = logging.getLogger(__name__)

# Fix encoding for Windows console - force UTF-8
if sys.platform == "win32":
    import io
    # Reconfigure stdout and stderr to use UTF-8 with error handling
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
else:
    # Ensure logs are flushed immediately for non-Windows systems
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)

# Detect if running in frozen mode (PyInstaller)
if getattr(sys, 'frozen', False):
    # If _MEIPASS is defined, we are in onefile mode (or onedir with internal bundle logic)
    # But for standard onedir (which we use), resources are relative to the executable
    if hasattr(sys, "_MEIPASS"):
        BASE_DIR = sys._MEIPASS
    else:
        BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    # Startup
    logger.info("="*60)
    logger.info("Application startup initiated")
    logger.info("="*60)
    
    # Ensure storage folders exist
    from file_storage_config import ensure_storage_folders_exist
    if ensure_storage_folders_exist():
        logger.info("✅ Storage folders initialized successfully")
    else:
        logger.warning("⚠️  Some storage folders could not be created")
    
    logger.info("Application startup completed")
    
    yield  # Application is running
    
    # Shutdown
    logger.info("="*60)
    logger.info("Application shutdown initiated")
    logger.info("="*60)
    
    logger.info("Application shutdown completed")

app = FastAPI(title="Smart Pricing API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # UXP Portal
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        # TODO: เพิ่ม production URLs
        # "https://uxp.company.com",
        # "https://smartpricing.company.com",
    ],
    allow_credentials=True,  # สำคัญ! ต้องเป็น True เพื่อรับ Cookie จาก UXP
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quotation_router, prefix="/api")
app.include_router(customer_router)
app.include_router(items_router,prefix="/api")
app.include_router(employees_router,prefix="/api")
app.include_router(login_router,prefix="/api")
app.include_router(pricing_router) # Router defines /api/pricing prefix internally
app.include_router(shipping_router) # Router defines /api/shipping prefix internally
app.include_router(cross_sell_router,prefix="/api")
app.include_router(invoice_router)
app.include_router(price_update_router, prefix="/api")
app.include_router(customer_analytics_router)
app.include_router(sq_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.include_router(cache_refresh_router)
app.include_router(admin_router, prefix="/api")
app.include_router(config_router, prefix="/api/config")
app.include_router(branch_router)
app.include_router(credit_router)
app.include_router(chrome_debug_router)  # Chrome debug mode starter
app.include_router(promotion_router)  # Promotion management
app.include_router(project_price_router)  # Project price management
app.include_router(special_price_request_router)  # Special price request management
app.include_router(print_router, prefix="/api")
app.include_router(product_image_router)  # Product image management
app.include_router(project_files_router)  # Project files management
app.include_router(statistics_router)  # Statistics management



# --- Static Files Serving (Fallback for Native App) ---
# When running as a native app (frozen) or if 'dist' exists nearby, serve frontend.
# In Docker, Nginx handles this, but this won't hurt as Nginx proxies /api and serves / itself.

dist_path = os.path.join(BASE_DIR, "dist")
if not os.path.exists(dist_path):
    # Try looking in the parent directory (development mode)
    dist_path = os.path.join(os.path.dirname(BASE_DIR), "frontend", "dist")

@app.get("/api/health")
def health_check():
    return {"status": "ok"}

# Mount product images directory (using config)
from file_storage_config import get_product_images_folder, get_project_files_folder

product_images_path = get_product_images_folder()
os.makedirs(product_images_path, exist_ok=True)
app.mount("/static/product-images", StaticFiles(directory=product_images_path), name="product-images")

# Mount project files directory (using config)
project_files_path = get_project_files_folder()
os.makedirs(project_files_path, exist_ok=True)
app.mount("/static/project-files", StaticFiles(directory=project_files_path), name="project-files")

if os.path.exists(dist_path):
    print(f"Serving static files from: {dist_path}")
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        # Allow API calls to pass through
        if (
            catchall.startswith("api/")
            or catchall.startswith("print/")
            or catchall.startswith("login")
        ):
            return Response(status_code=404)


        # Check if file exists in dist
        file_path = os.path.join(dist_path, catchall)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # Fallback to index.html for SPA routing
        return FileResponse(os.path.join(dist_path, "index.html"))

if __name__ == "__main__":
    # ⭐ ตรวจสอบว่าอยู่ใน RPA mode หรือไม่
    # ถ้าใช่ ไม่ต้องรัน FastAPI server
    if os.getenv('RPA_MODE') == '1':
        logger.info("Running in RPA mode - skipping FastAPI server startup")
        sys.exit(0)
    
    import uvicorn
    
    print("--- Starting Server ---")
    logger.info("Starting Smart Pricing API server")

    # Check for required API keys
    if not CUSTOMER_API_KEY:
        warning_msg = "CUSTOMER_API_KEY is not set or empty! Please create a .env file with your API keys."
        logger.warning(warning_msg)
        print("\n" + "="*60)
        print(f" [WARNING] {warning_msg}")
        print("="*60 + "\n")
    
    # Check for Item Master sync API keys
    item_api_url = os.getenv("ITEM_API_URL")
    item_api_key = os.getenv("ITEM_API_KEY")
    if not item_api_url or not item_api_key:
        warning_msg = "ITEM_API_URL or ITEM_API_KEY not set. Item Master sync will not work."
        logger.warning(warning_msg)
        print(f"WARNING: {warning_msg}")

    # Pass the app object directly instead of the import string "main:app"
    # This prevents "Could not import module 'main'" errors in frozen (PyInstaller) environments
    logger.info("Starting uvicorn server on 0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False, log_level="info")


#uvicorn main:app --reload --port 8000
#npx prettier --write src
