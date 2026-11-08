$ErrorActionPreference = 'Stop'
$podnotesRoot = Split-Path -Parent $PSScriptRoot
$podnotesPython = Join-Path $podnotesRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $podnotesPython)) {
    throw 'Project virtual environment not found. No processes were stopped.'
}

# Make a consistent backup before opening the upgraded application/database.
& $podnotesPython (Join-Path $PSScriptRoot 'backup_miniprogram_store.py')
if ($LASTEXITCODE -ne 0) { throw 'Database backup failed. Upgrade stopped.' }

$podnotesListeners = @(Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($podnotesListener in $podnotesListeners) {
    $podnotesProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $podnotesListener"
    if ($podnotesProcess.CommandLine -notmatch 'run_miniprogram_server\.py|backend\.mini\.app') {
        throw "Port 8010 process $podnotesListener could not be identified as the mini API. No stop was attempted for this process."
    }
    Write-Host "Stopping existing mini API PID $podnotesListener"
    Stop-Process -Id $podnotesListener -ErrorAction Stop
    $podnotesRemaining = Get-Process -Id $podnotesListener -ErrorAction SilentlyContinue
    if ($podnotesRemaining) { Wait-Process -Id $podnotesListener -Timeout 10 -ErrorAction Stop }
}

Write-Host 'Starting dialogue worker protocol 4. Keep this window open.'
& $podnotesPython (Join-Path $PSScriptRoot 'run_miniprogram_server.py') --mode dialogue --daily-limit 20
if ($LASTEXITCODE -ne 0) { throw 'API did not start successfully; retain the error output for diagnosis.' }
