"""Read-only Windows inventory. Inventory is never proof of leak protection."""
from datetime import datetime, timezone
import json
from . import windows

INVENTORY_SCRIPT = r'''
$os = Get-CimInstance Win32_OperatingSystem
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$apps = @()
foreach ($exe in @('msedge.exe','chrome.exe','firefox.exe','brave.exe','vivaldi.exe','opera.exe')) {
    foreach ($root in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths', 'HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths')) {
        $key = Join-Path $root $exe
        if (Test-Path $key) {
            $path = (Get-Item $key).GetValue('')
            if ($path -and (Test-Path -LiteralPath $path)) {
                $apps += [ordered]@{exe=$exe; path=$path; version=(Get-Item -LiteralPath $path).VersionInfo.ProductVersion}
            }
        }
    }
}
$internet = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
[ordered]@{
    os=[ordered]@{caption=$os.Caption; version=$os.Version; build=$os.BuildNumber; architecture=$os.OSArchitecture}
    administrator=$admin
    system=[ordered]@{timezone=(Get-TimeZone).Id; culture=(Get-Culture).Name; system_locale=(Get-WinSystemLocale).Name}
    adapters=@(Get-NetAdapter | Select-Object Name,InterfaceDescription,ifIndex,Status)
    default_routes=@(Get-NetRoute | Where-Object { $_.DestinationPrefix -in @('0.0.0.0/0','::/0','0.0.0.0/1','128.0.0.0/1','::/1','8000::/1') } | Select-Object DestinationPrefix,InterfaceIndex,NextHop,RouteMetric)
    dns=@(Get-DnsClientServerAddress | Select-Object InterfaceIndex,InterfaceAlias,AddressFamily,ServerAddresses)
    user_proxy=[ordered]@{enabled=[bool]$internet.ProxyEnable; pac_configured=[bool]$internet.AutoConfigURL}
    registered_browsers=$apps
    running_browsers=@(Get-Process -Name msedge,chrome,firefox,brave,vivaldi,opera -ErrorAction SilentlyContinue | Select-Object ProcessName,Id)
    proxy_processes=@(Get-Process -Name mihomo,clash,clash-meta,sing-box -ErrorAction SilentlyContinue | Select-Object ProcessName,Id)
} | ConvertTo-Json -Depth 8 -Compress
'''


def collect():
    inventory = json.loads(windows.powershell(INVENTORY_SCRIPT))
    return {
        'schema': 1,
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'read_only': True,
        'inventory': inventory,
        'browser_inventory_scope': 'Registered App Paths only; portable/unregistered browsers may be absent',
        'verification': {name: {'status': 'unverified', 'reason': reason} for name, reason in {
            'whole_host_routing': 'Interface and route inventory does not prove that every application is covered',
            'ipv4_ipv6_egress': 'External egress and bypass probes have not run',
            'dns_leak': 'Resolver observation or packet capture has not run',
            'webrtc_leak': 'ICE probes in installed browser profiles have not run',
            'proxy_failure_blocking': 'Controlled proxy interruption test has not run',
        }.items()},
        'overall': 'unverified',
    }
