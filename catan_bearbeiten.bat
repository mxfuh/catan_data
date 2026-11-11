@echo off
rem Catan-Daten sicher von Hand bearbeiten:
rem 1. neuesten Stand von GitHub holen (auch Eintraege des Bots)
rem 2. Excel oeffnen und warten, bis sie wieder geschlossen ist
rem 3. Aenderungen sofort committen und pushen (loest die Prognose aus)
setlocal
rem Wartepausen per ping: funktioniert auch ohne Konsole und wenn Git-Tools im PATH stehen
cd /d "%~dp0"
set FILE=catan_data.xlsx
set LOCK=~$catan_data.xlsx

if exist "%LOCK%" (
    echo Die Excel ist noch geoeffnet. Bitte erst schliessen, dann nochmal starten.
    pause
    exit /b 1
)

echo Hole neuesten Stand von GitHub ...
git pull --rebase
if errorlevel 1 (
    echo.
    echo Pull fehlgeschlagen - bitte nichts bearbeiten und Claude Bescheid geben.
    pause
    exit /b 1
)

echo Oeffne %FILE% ... Dieses Fenster wartet, bis du die Excel schliesst.
start "" "%FILE%"

rem Warten, bis Excel die Datei geoeffnet hat (Sperrdatei erscheint), max. 2 Minuten
set /a N=0
:wait_open
if exist "%LOCK%" goto wait_close
set /a N+=1
if %N% geq 60 (
    echo Excel scheint die Datei nicht geoeffnet zu haben - Abbruch, nichts wurde veraendert.
    pause
    exit /b 1
)
ping -n 3 127.0.0.1 >nul
goto wait_open

rem Warten, bis die Excel wieder geschlossen ist (Sperrdatei verschwindet)
:wait_close
ping -n 3 127.0.0.1 >nul
if exist "%LOCK%" goto wait_close

git diff --quiet -- "%FILE%"
if not errorlevel 1 (
    echo Keine Aenderungen gespeichert - nichts zu tun.
    pause
    exit /b 0
)

git add "%FILE%"
git commit -m "data update"
git push
if errorlevel 1 (
    echo.
    echo Push fehlgeschlagen - deine Aenderung ist lokal committet. Bitte Claude Bescheid geben.
    pause
    exit /b 1
)
echo.
echo Fertig und auf GitHub. Ist ein neues Spiel mit Pre-Game-Daten dabei, kommt die Prognose in ca. 3 Minuten.
pause
