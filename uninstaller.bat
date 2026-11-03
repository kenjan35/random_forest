@echo off
cd /d "%~dp0"

rem --- Python du systeme (jamais celui du dossier venv, qui va etre supprime)
where py >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=py -3"
    set "PYWCMD=pyw -3"
) else (
    set "PYCMD=python"
    set "PYWCMD=pythonw"
)

%PYCMD% -c "import tkinter" >nul 2>nul
if %errorlevel%==0 (
    start "" %PYWCMD% "%~dp0uninstaller_gui.py"
    if not errorlevel 1 exit /b 0
    %PYCMD% "%~dp0uninstaller_gui.py"
    exit /b 0
)

rem --- Repli en mode texte (Python absent ou sans tkinter)
echo ================================================
echo   Desinstallation - Detection de vol de carburant
echo ================================================
echo.
echo Seront supprimes : l'environnement (dossier venv), le raccourci du Bureau
echo et les fichiers temporaires. Le code, le modele, les donnees et les
echo rapports sont conserves.
echo.
choice /c ON /m "Continuer la desinstallation ? (O = oui, N = non)"
if errorlevel 2 exit /b 0

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Fuel Theft Detector.lnk'; if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Force }"
if exist venv (
    rmdir /s /q venv
    if exist venv (
        echo.
        echo ERREUR : certains fichiers sont utilises. Fermez l'application puis relancez ce fichier.
        pause
        exit /b 1
    )
)
for /d /r %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d"
echo.
echo Desinstallation terminee. Pour retirer completement l'application,
echo supprimez ensuite ce dossier : %~dp0
pause
