@echo off
cd /d "%~dp0"

rem --- Python est indispensable (l'installateur graphique est ecrit en Python)
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=py -3"
    set "PYWCMD=pyw -3"
) else (
    set "PYCMD=python"
    set "PYWCMD=pythonw"
)

%PYCMD% -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo ================================================
    echo   Installation - Detection de vol de carburant
    echo ================================================
    echo.
    echo ERREUR : Python introuvable sur cette machine.
    echo Installez Python 64 bits depuis https://www.python.org/downloads/
    echo N'oubliez pas de cocher "Add python.exe to PATH" pendant l'installation.
    echo Relancez ensuite ce fichier.
    pause
    exit /b 1
)

rem --- Installateur graphique (tkinter est fourni avec Python sous Windows)
%PYCMD% -c "import tkinter" >nul 2>nul
if %errorlevel%==0 (
    start "" %PYWCMD% "%~dp0installer_gui.py"
    if not errorlevel 1 exit /b 0
    %PYCMD% "%~dp0installer_gui.py"
    exit /b 0
)

rem --- Repli : installation en mode texte si tkinter n'est pas disponible
echo ================================================
echo   Installation - Detection de vol de carburant
echo ================================================
echo.
%PYCMD% -m venv venv
if errorlevel 1 (
    echo ERREUR : impossible de creer l'environnement de l'application.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-gui.txt
if errorlevel 1 (
    echo.
    echo ERREUR pendant l'installation des composants : verifiez la connexion Internet.
    pause
    exit /b 1
)
echo.
echo Installation terminee. Utilisez lancer.bat pour ouvrir l'application.
pause