[CmdletBinding()]
param([switch]$SkipTimer, [switch]$SkipBrowsers)
$ErrorActionPreference = 'Stop'
$Project = $PSScriptRoot
$Python = Join-Path $Project '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    if (Get-Command py.exe -ErrorAction SilentlyContinue) {
        & py.exe -3 -m venv (Join-Path $Project '.venv')
    } elseif (Get-Command python.exe -ErrorAction SilentlyContinue) {
        & python.exe -m venv (Join-Path $Project '.venv')
    } else {
        throw 'Install Python 3.10 or newer with the Python launcher, then run this installer again.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create the Python virtual environment.' }
}
& $Python -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ required.' }
& $Python -m pip install -e $Project
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
if (-not $SkipBrowsers) {
    & $Python -m playwright install firefox chromium
    if ($LASTEXITCODE -ne 0) { throw 'Browser installation failed. Retry, or use -SkipBrowsers for host-only operation.' }
}
$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if (($UserPath -split ';') -notcontains $Project) {
    $NewPath = if ([string]::IsNullOrEmpty($UserPath)) { $Project } else { $UserPath.TrimEnd(';') + ';' + $Project }
    [Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
}
if (($env:Path -split ';') -notcontains $Project) { $env:Path += ';' + $Project }
if (-not $SkipTimer) {
    & $Python -m r0env install
    if ($LASTEXITCODE -ne 0) { throw 'Scheduled task installation failed. Retry r0env install.' }
}
Write-Host 'Installed. Open a new terminal and run: r0env help'
Write-Host 'Use an administrator terminal for r0env apply. Keep this project folder in place.'
