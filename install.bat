@echo off
chcp 65001 >nul

echo.
echo ====================================================================
echo    MOLTBOOK LOCAL AGENT - Installation Script
echo ====================================================================
echo.
timeout /t 1 >nul
    
echo [1/6] Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python not found! Please install Python 3.10+ first.
    echo         Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] Python %PYTHON_VERSION% detected
echo.

echo [2/6] Checking for CUDA support...
where nvidia-smi >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] nvidia-smi not found - No NVIDIA GPU detected
    echo           Installing CPU-only version of PyTorch...
    set TORCH_INSTALL=pip3 install torch torchvision torchaudio
) else (
    echo [OK] NVIDIA GPU detected!
    nvidia-smi --query-gpu=name,driver_version,cuda_version --format=csv,noheader
    echo [OK] Installing PyTorch with CUDA 12.6 support...
    set TORCH_INSTALL=pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
)
echo.

echo [3/6] Creating virtual environment...
if exist env (
    echo [WARNING] Virtual environment already exists, skipping creation
) else (
    python -m venv env
    echo [OK] Virtual environment created
)
echo.

echo [4/6] Activating virtual environment...
call env\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

echo [5/6] Installing PyTorch...
echo --------------------------------------------------------------------
%TORCH_INSTALL%
if %errorlevel% neq 0 (
    echo [ERROR] PyTorch installation failed
    pause
    exit /b 1
)
echo [OK] PyTorch installed successfully
echo.

echo [6/6] Installing requirements...
echo --------------------------------------------------------------------
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Requirements installation failed
    pause
    exit /b 1
)
echo [OK] All requirements installed
echo.

echo ====================================================================
echo    INSTALLATION COMPLETE!
echo ====================================================================
echo.
echo Next steps:
echo   1. Copy .env.example to .env and configure your API keys
echo   2. Download a GGUF model to the models/ directory
echo   3. Run: python main.py
echo.
echo Press any key to exit...
pause >nul