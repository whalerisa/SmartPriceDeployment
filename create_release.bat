@echo off
setlocal

echo ==================================================
echo      SMART PRICING - RELEASE BUILDER
echo ==================================================

echo 1. Building Frontend...
cd frontend
call npm install
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b %errorlevel%
)
cd ..

echo 2. Installing Backend Requirements...
cd backend
pip install -r requirements.txt
cd ..

echo 3. Running PyInstaller...
pyinstaller --noconfirm --clean smart_pricing.spec

echo 4. Copying JSON configuration files...
copy backend\page_access_config.json dist\smart_pricing\
copy backend\role_approval_scope.json dist\smart_pricing\
copy backend\custom_roles.json dist\smart_pricing\
copy backend\employees.json dist\smart_pricing\

echo 5. Finalizing Release...
copy start_server.bat dist\smart_pricing\
copy DEPLOYMENT.md dist\smart_pricing\

echo ==================================================
echo      BUILD COMPLETE
echo ==================================================
echo The executable is located in 'dist/smart_pricing/'
echo You can zip this folder and move it to your offline server.
pause
