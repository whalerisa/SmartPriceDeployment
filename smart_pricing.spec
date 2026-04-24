# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None

# Define paths
backend_path = os.path.abspath('backend')
frontend_dist_path = os.path.abspath(os.path.join('frontend', 'dist'))

# Ensure frontend dist exists (verification step for user, though spec runs during build)
if not os.path.exists(frontend_dist_path):
    print(f"WARNING: Frontend dist path not found at {frontend_dist_path}")
    print("Please run 'npm run build' in frontend directory first.")

# Collect hidden imports for scipy (common issue)
hidden_imports = [
    'scipy.special.cython_special',
    'scipy.spatial.transform._rotation_groups',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'engineio.async_drivers.threading', # If using socketio, but good measure
    'selenium',
    'selenium.webdriver',
    'selenium.webdriver.chrome',
    'selenium.webdriver.chrome.options',
    'selenium.webdriver.common.by',
    'selenium.webdriver.support',
    'selenium.webdriver.support.ui',
    'selenium.webdriver.support.expected_conditions',
    'selenium.webdriver.common.action_chains',
    'selenium.webdriver.common.keys',
]

datas = [
    (backend_path + '/config/data', 'config/data'), # Database and excel files
    (frontend_dist_path, 'dist'),    # Frontend static files
    (backend_path + '/quotation.html', '.'), # Templates
    (backend_path + '/Sarabun-Regular.ttf', '.'), # Fonts
    # JSON configuration files
    (backend_path + '/page_access_config.json', '.'),
    (backend_path + '/role_approval_scope.json', '.'),
    (backend_path + '/custom_roles.json', '.'),
    (backend_path + '/employees.json', '.'),
    # mean_sd.json removed - statistics now calculated from database
]

# WeasyPrint / Pango / GDK DLLs need to be reachable or bundled if not system installed.
# Usually on Windows, we rely on GTK3 runtime being installed by user.
# But we can try to collect them if we knew where they were.
# For now, we assume GTK3 Runtime is installed as per plan.

a = Analysis(
    [os.path.join(backend_path, 'main.py')],
    pathex=[backend_path],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PyQt5', 'PySide2', 'PyQt6', 'PySide6'], # Exclude GUI frameworks to save space
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='smart_pricing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='smart_pricing',
)
