@echo off
setlocal EnableExtensions
title Installation - Detection de vol de carburant
pushd "%~dp0"
set "ROOT=%~dp0"

rem ==================================================================
rem  Si aucun Python compatible (3.11 a 3.14, 64 bits) n'est present,
rem  Python 3.13 est telecharge et installe automatiquement pour
rem  l'utilisateur courant : aucun droit administrateur requis.
rem
rem  Pour eviter le telechargement de Python : placer le fichier
rem  python-3.13.17-amd64.exe dans ce dossier, a cote de ce script.
rem ==================================================================
set "PY_VERSION=3.13.17"
set "PY_DIR=Python313"
set "PY_SETUP_NAME=python-%PY_VERSION%-amd64.exe"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/%PY_SETUP_NAME%"
set "PY_TARGET=%LOCALAPPDATA%\Programs\Python\%PY_DIR%"
set "PY_LOG=%TEMP%\installation-python.log"
set "VENV_PY=%ROOT%venv\Scripts\python.exe"
set "PY_EXE="
set "PY_ARG="
set "SETUP_CODE=0"

echo.
echo  ==========================================================
echo     Installation - Detection de vol de carburant
echo  ==========================================================
echo.

if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 (
    echo  [ERREUR] Windows 32 bits detecte : l'application necessite Windows 64 bits.
    goto :fail
)

rem --- Environnement deja en place : relance apres une mise a jour ---
if exist "%VENV_PY%" (
    call :check "%VENV_PY%"
    if not errorlevel 1 (
        echo  [1/3] Python : deja installe.
        echo  [2/3] Environnement de l'application : deja present.
        goto :deps
    )
    echo  Environnement existant incompatible ou endommage : il va etre recree.
    rmdir /s /q "%ROOT%venv"
)

rem --- 1. Python ---------------------------------------------------
echo  [1/3] Recherche d'une version compatible de Python...
call :pick "%PY_TARGET%\python.exe"
call :pick "%ProgramFiles%\%PY_DIR%\python.exe"
call :pick python
call :pick py -3.13
call :pick py -3.12
call :pick py -3.11
call :pick py -3.14
if defined PY_EXE (
    echo        Python compatible trouve.
    goto :create_venv
)

echo        Aucune version compatible : installation automatique de Python %PY_VERSION%.
echo        Aucun droit administrateur n'est necessaire.

set "PY_SETUP=%ROOT%%PY_SETUP_NAME%"
call :setup_ok
if not errorlevel 1 (
    echo        Installateur trouve dans le dossier : pas de telechargement.
    goto :run_setup
)

set "PY_SETUP=%TEMP%\%PY_SETUP_NAME%"
echo        Telechargement depuis python.org, environ 30 Mo...
del /f /q "%PY_SETUP%" >nul 2>&1
curl.exe -L --fail --retry 2 -# -o "%PY_SETUP%" "%PY_URL%"
call :setup_ok
if not errorlevel 1 goto :run_setup

rem Second essai : PowerShell utilise le proxy et les certificats de Windows
echo        Nouvel essai du telechargement...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing -Uri $env:PY_URL -OutFile $env:PY_SETUP"
call :setup_ok
if not errorlevel 1 goto :run_setup

echo.
echo  [ERREUR] Impossible de telecharger Python.
echo  Verifiez la connexion Internet, ou placez le fichier %PY_SETUP_NAME%
echo  dans ce dossier puis relancez installer.bat.
echo  Lien direct : %PY_URL%
goto :fail

:run_setup
echo        Installation de Python en cours, 1 a 3 minutes...
start "" /wait "%PY_SETUP%" /quiet InstallAllUsers=0 TargetDir="%PY_TARGET%" PrependPath=1 Include_launcher=0 Include_test=0 Include_doc=0 Shortcuts=0 /log "%PY_LOG%"
set "SETUP_CODE=%errorlevel%"
if "%SETUP_CODE%"=="3010" set "SETUP_CODE=0"
if not "%SETUP_CODE%"=="0" goto :setup_failed
set "PY_EXE="
call :pick "%PY_TARGET%\python.exe"
if not defined PY_EXE goto :setup_failed
if /i "%PY_SETUP%"=="%TEMP%\%PY_SETUP_NAME%" del /f /q "%PY_SETUP%" >nul 2>&1
echo        Python %PY_VERSION% installe.

rem --- 2. Environnement de l'application ------------------------------
:create_venv
echo  [2/3] Creation de l'environnement de l'application...
"%PY_EXE%" %PY_ARG% -m venv "%ROOT%venv"
if errorlevel 1 goto :venv_failed

rem --- 3. Bibliotheques --------------------------------------------
:deps
echo  [3/3] Installation des bibliotheques, plusieurs minutes la premiere fois...
"%VENV_PY%" -m pip install --upgrade pip --disable-pip-version-check -q
"%VENV_PY%" -m pip install --disable-pip-version-check -r "%ROOT%requirements-gui.txt"
if errorlevel 1 goto :deps_failed

echo.
echo  ==========================================================
echo     Installation terminee.
echo     Lancez l'application avec lancer.bat
echo  ==========================================================
echo.
pause
popd
exit /b 0

rem ==================================================================
rem  Erreurs
rem ==================================================================
:setup_failed
echo.
echo  [ERREUR] L'installation de Python a echoue, code %SETUP_CODE%.
if "%SETUP_CODE%"=="0" echo  Python semble installe mais reste introuvable dans : %PY_TARGET%
if "%SETUP_CODE%"=="1602" echo  L'installation a ete annulee.
if "%SETUP_CODE%"=="1618" echo  Une autre installation Windows est en cours : attendez la fin puis relancez.
echo  Journal detaille : %PY_LOG%
goto :fail

:venv_failed
echo.
echo  [ERREUR] Impossible de creer l'environnement dans :
echo  %ROOT%venv
goto :fail

:deps_failed
echo.
echo  [ERREUR] L'installation des bibliotheques a echoue.
echo  Verifiez la connexion Internet puis relancez installer.bat :
echo  les bibliotheques deja telechargees ne seront pas retelechargees.
goto :fail

:fail
echo.
pause
popd
exit /b 1

rem ==================================================================
rem  Sous-routines
rem ==================================================================

rem Code 0 si l'executable %1 (argument optionnel %2) est un Python 64 bits
rem en version 3.11 a 3.14, celles que supporte scikit-learn 1.9.0
:check
"%~1" %~2 -c "import sys; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 14) and sys.maxsize > 2**32 else 1)" >nul 2>&1
exit /b %errorlevel%

rem Retient le premier Python compatible trouve
:pick
if defined PY_EXE exit /b 0
call :check "%~1" "%~2"
if errorlevel 1 exit /b 0
set "PY_EXE=%~1"
set "PY_ARG=%~2"
exit /b 0

rem Code 0 si l'installateur existe et n'est pas tronque
:setup_ok
if not exist "%PY_SETUP%" exit /b 1
for %%F in ("%PY_SETUP%") do if %%~zF LSS 10000000 exit /b 1
exit /b 0