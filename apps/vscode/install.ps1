[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App vscode -RepositoryRoot $RepositoryRoot)) {
    return
}
Get-SnowyOwlFontSelection -RepositoryRoot $RepositoryRoot -App vscode -Role monospace | Out-Null

$Vsix = Get-ChildItem (Join-Path $RepositoryRoot 'dist/*.vsix') -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $Vsix) {
    $Vsix = Get-ChildItem (Join-Path $PSScriptRoot '*.vsix') -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    Write-SnowyOwlMessage 'VS Code CLI (code) not found.'
    return
}
if (-not $Vsix) {
    Write-SnowyOwlMessage 'No VSIX found. Run scripts/build.ps1 -All or download a release.'
    return
}

& code --install-extension $Vsix.FullName --force
Write-SnowyOwlMessage 'VS Code VSIX installed.'
