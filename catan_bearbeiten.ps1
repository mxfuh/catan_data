# Catan-Daten sicher von Hand bearbeiten (wird von catan_bearbeiten.bat gestartet):
# 1. neuesten Stand von GitHub holen (auch Einträge des Bots)
# 2. Excel öffnen und warten, bis das Excel-Fenster wieder geschlossen ist
# 3. Änderungen sofort committen und pushen (löst die Prognose aus)
# Erkennung über den Fenstertitel statt über die Sperrdatei ~$..., weil Excel diese
# bei Dateien in OneDrive-Ordnern oft nicht anlegt.
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot
$file = 'catan_data.xlsx'
Add-Type -AssemblyName UIAutomationClient

function Test-ExcelOpen {
    # true, wenn ein Excel-Fenster mit "catan_data" im Titel offen ist (der Explorer-Ordner heißt genauso)
    $root = [System.Windows.Automation.AutomationElement]::RootElement
    $windows = $root.FindAll([System.Windows.Automation.TreeScope]::Children,
                             [System.Windows.Automation.Condition]::TrueCondition)
    foreach ($w in $windows) {
        try {
            if ($w.Current.Name -like '*catan_data*') {
                $p = Get-Process -Id $w.Current.ProcessId -ErrorAction SilentlyContinue
                if ($p -and $p.ProcessName -eq 'EXCEL') { return $true }
            }
        } catch { }  # Fenster kann zwischendurch verschwinden
    }
    return $false
}

function Exit-WithMessage([string]$message, [int]$code) {
    Write-Host ''
    Write-Host $message
    Read-Host 'Enter zum Schließen' | Out-Null
    exit $code
}

if (Test-ExcelOpen) { Exit-WithMessage 'Die Excel ist noch geöffnet. Bitte erst schließen, dann nochmal starten.' 1 }

Write-Host 'Hole neuesten Stand von GitHub ...'
git pull --rebase
if ($LASTEXITCODE -ne 0) { Exit-WithMessage 'Pull fehlgeschlagen - bitte nichts bearbeiten und Claude Bescheid geben.' 1 }

Write-Host "Öffne $file ... Dieses Fenster wartet, bis du die Excel schließt."
Start-Process (Join-Path $PSScriptRoot $file)

# Warten, bis das Excel-Fenster erscheint (max. 90 s), dann bis es wieder weg ist
$deadline = (Get-Date).AddSeconds(90)
while (-not (Test-ExcelOpen) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 1 }
if (Test-ExcelOpen) {
    while (Test-ExcelOpen) { Start-Sleep -Seconds 2 }
} else {
    Read-Host 'Excel-Fenster nicht erkannt. Drücke Enter, sobald du fertig bist und die Excel geschlossen hast' | Out-Null
}

# Gespeicherte Änderung abwarten (OneDrive/Excel schreiben evtl. kurz nach), max. 15 s
$changed = $false
for ($i = 0; $i -lt 15; $i++) {
    git diff --quiet -- $file
    if ($LASTEXITCODE -ne 0) { $changed = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $changed) { Exit-WithMessage 'Keine Änderungen gespeichert - nichts zu tun.' 0 }

git add $file
git commit -m 'data update'
git push
if ($LASTEXITCODE -ne 0) { Exit-WithMessage 'Push fehlgeschlagen - deine Änderung ist lokal committet. Bitte Claude Bescheid geben.' 1 }
Exit-WithMessage 'Fertig und auf GitHub. Ist ein neues Spiel mit Pre-Game-Daten dabei, kommt die Prognose in ca. 3 Minuten.' 0
