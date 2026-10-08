Set-Location $PSScriptRoot
. .\venv\Scripts\Activate.ps1
Start-Process "http://localhost:5000/dashboard"
python app.py
