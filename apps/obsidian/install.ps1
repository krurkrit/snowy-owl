[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App obsidian -RepositoryRoot $RepositoryRoot)) {
    return
}
Get-SnowyOwlFontSelection -RepositoryRoot $RepositoryRoot -App obsidian -Role ui | Out-Null
Get-SnowyOwlFontSelection -RepositoryRoot $RepositoryRoot -App obsidian -Role monospace | Out-Null

$VaultPath = $Options.ObsidianVault
if (-not $VaultPath) {
    Write-SnowyOwlMessage 'Obsidian needs -ObsidianVault <vault path>.'
    return
}

$Destination = Join-Path $VaultPath '.obsidian/snippets'
New-Item -ItemType Directory -Force -Path $Destination | Out-Null
$SourcePath = Join-Path $RepositoryRoot 'generated/obsidian/snowy-owl.css'
Copy-Item -LiteralPath $SourcePath -Destination (Join-Path $Destination 'snowy-owl.css') -Force
Write-SnowyOwlMessage 'Obsidian snippet installed. Enable it in Appearance > CSS snippets.'
