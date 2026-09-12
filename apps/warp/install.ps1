[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App warp -RepositoryRoot $RepositoryRoot)) {
    return
}
Get-SnowyOwlFontSelection -RepositoryRoot $RepositoryRoot -App warp -Role monospace | Out-Null

$IsWindowsPlatform = [Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
    [Runtime.InteropServices.OSPlatform]::Windows
)
$IsMacOSPlatform = [Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
    [Runtime.InteropServices.OSPlatform]::OSX
)
if ($IsWindowsPlatform) {
    $Destination = Join-Path $env:APPDATA 'warp-terminal/themes'
}
elseif ($IsMacOSPlatform) {
    $Destination = Join-Path $HOME '.warp/themes'
}
else {
    $Destination = Join-Path $HOME '.local/share/warp-terminal/themes'
}

New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$Source = Join-Path $RepositoryRoot 'generated/warp/snowy-owl-*.yaml'
Copy-Item -Path $Source -Destination $Destination -Force
Write-SnowyOwlMessage "Warp themes copied to $Destination. Select Snowy Owl in Warp Appearance."
