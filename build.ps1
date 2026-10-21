# Builds dist\CoordX\CoordX.exe on Windows (used by GitHub Actions; also works locally).
$ErrorActionPreference = "Stop"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller==6.22.3
python -m PyInstaller --noconfirm --clean --windowed --name CoordX `
  --icon assets\icon.ico `
  --add-data "assets;assets" `
  --collect-data rapidocr_onnxruntime `
  --exclude-module tkinter `
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets `
  --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtQuick --exclude-module PySide6.QtQml `
  --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtCharts --exclude-module PySide6.QtDataVisualization `
  main.py
