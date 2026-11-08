$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$config = Get-Content -LiteralPath (Join-Path $root 'config\managed-runtime.json') -Raw | ConvertFrom-Json
$mutex = New-Object System.Threading.Mutex($false, 'Global\PodnotesMiniSupervisor')
try { $locked = $mutex.WaitOne(0) } catch [System.Threading.AbandonedMutexException] { $locked = $true }
if (-not $locked) { exit 0 }
try {
    Add-Type -AssemblyName System.Security
    $cipher = [IO.File]::ReadAllBytes((Join-Path $root 'config\ops-secrets\wechat-secret.bin'))
    $plain = [Security.Cryptography.ProtectedData]::Unprotect($cipher, $null, [Security.Cryptography.DataProtectionScope]::LocalMachine)
    $env:WECHAT_APP_SECRET = [Text.Encoding]::UTF8.GetString($plain)
    [Array]::Clear($plain, 0, $plain.Length)
    $env:PYTHONIOENCODING = 'utf-8'
    $env:MINI_DATA_DIR = Join-Path $root 'data\miniprogram-server'
    $env:MODELSCOPE_CACHE = Join-Path $root 'data\model-cache\modelscope'
    $env:HF_HOME = Join-Path $root 'data\model-cache\huggingface'
    $env:PATH = $config.ffmpeg_directory + ';' + $env:PATH
    $logFolder = Join-Path $root 'data\managed-api-logs'
    New-Item -ItemType Directory -Path $logFolder -Force | Out-Null
    $failures = 0
    while ($true) {
        $listener = @(Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue)
        if ($listener.Count -gt 0) { throw 'Port 8010 already occupied. Supervisor did not stop the existing listener.' }
        $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
        $child = Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') -ArgumentList @('scripts\run_miniprogram_server.py','--mode','dialogue','--daily-limit',([string]$config.daily_limit)) -WorkingDirectory $root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logFolder "managed-api-$stamp.stdout.log") -RedirectStandardError (Join-Path $logFolder "managed-api-$stamp.stderr.log") -PassThru
        $badHealth = 0
        $lastHealthy = $null
        while (-not $child.HasExited) {
            Start-Sleep -Seconds 10
            if ($child.HasExited) { break }
            try {
                $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8010/mini/health' -TimeoutSec 3
                if ($health.worker_protocol -ne 4 -or -not $health.worker_alive) { throw 'Worker unavailable' }
                $badHealth = 0
                $lastHealthy = (Get-Date).ToUniversalTime().ToString('o')
                @{status='healthy';launcher_pid=$child.Id;last_healthy_utc=$lastHealthy;restart_count=$failures} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logFolder 'supervisor-status.json') -Encoding UTF8
            } catch { $badHealth++ }
            if ($badHealth -ge 3) {
                # This PID is the exact child we created; /T includes its venv Python child.
                & "$env:SystemRoot\System32\taskkill.exe" /PID $child.Id /T /F | Out-Null
                break
            }
        }
        $failures++
        @{status='restarting';last_healthy_utc=$lastHealthy;restart_count=$failures} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $logFolder 'supervisor-status.json') -Encoding UTF8
        Start-Sleep -Seconds ([Math]::Min(60, 5 * $failures))
    }
} finally {
    Remove-Item Env:\WECHAT_APP_SECRET -ErrorAction SilentlyContinue
    if ($locked) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
}
