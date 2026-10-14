[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$TaskName = 'r0env2-check-' + $env:USERNAME
Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$NewPath = (($UserPath -split ';') | Where-Object { $_ -and $_ -ne $PSScriptRoot }) -join ';'
[Environment]::SetEnvironmentVariable('Path', $NewPath, 'User')
Write-Host 'Removed scheduled task and user PATH entry. Project files, logs, snapshots and OS settings were preserved.'
Write-Host 'Use r0env restore SNAPSHOT before removing the project if you need to restore OS settings.'
