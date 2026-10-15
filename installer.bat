@echo off
cd /d "%~dp0"

echo ================================================
echo   Installation - Detection de vol de carburant
echo ================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=py -3"
) else (
    set "PYCMD=python"
)

%PYCMD% -m venv venv
if errorlevel 1 (
    echo ERREUR : Python introuvable sur cette machine.
    echo Installez Python depuis https://www.python.org/downloads/
    echo N'oubliez pas de cocher "Add python.exe to PATH" pendant l'installation.
    echo Relancez ensuite ce fichier.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt

echo.
echo Installation terminee. Utilisez lancer.bat pour ouvrir l'application.
pause