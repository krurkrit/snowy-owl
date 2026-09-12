[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App windows-terminal -RepositoryRoot $RepositoryRoot)) {
    return
}

$SettingsPaths = @(
    (Join-Path $env:LOCALAPPDATA 'Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json')
    (Join-Path $env:LOCALAPPDATA 'Packages/Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe/LocalState/settings.json')
    (Join-Path $env:LOCALAPPDATA 'Microsoft/Windows Terminal/settings.json')
)
$SettingsPath = $SettingsPaths | Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $SettingsPath) {
    Write-SnowyOwlMessage 'Windows Terminal settings.json not found. Open Terminal Settings once, then retry.'
    return
}

Backup-SnowyOwlFile $SettingsPath
$Settings = Get-Content -Raw -LiteralPath $SettingsPath | ConvertFrom-Json -Depth 100
$SourcePath = Join-Path $RepositoryRoot 'generated/windows-terminal/snowy-owl-schemes.json'
$Source = Get-Content -Raw -LiteralPath $SourcePath | ConvertFrom-Json -Depth 100
$InstalledFont = Get-SnowyOwlFontSelection -RepositoryRoot $RepositoryRoot -App windows-terminal -Role monospace
if ($InstalledFont) {
    $Source.profileDefaults.font.face = $InstalledFont.family
    $Source.profileDefaults.font.weight = $InstalledFont.weight
}

if (-not $Settings.schemes) {
    $Settings | Add-Member NoteProperty schemes @()
}
$Settings.schemes = @($Settings.schemes | Where-Object { $_.name -notlike 'Snowy Owl*' }) +
    @($Source.schemes)
if (-not $Settings.profiles) {
    $Settings | Add-Member NoteProperty profiles ([pscustomobject]@{})
}
if (-not $Settings.profiles.defaults) {
    $Settings.profiles | Add-Member NoteProperty defaults ([pscustomobject]@{})
}
$Settings.profiles.defaults |
    Add-Member NoteProperty colorScheme $Source.profileDefaults.colorScheme -Force
$Settings.profiles.defaults |
    Add-Member NoteProperty font $Source.profileDefaults.font -Force
$Settings | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $SettingsPath -Encoding utf8
Write-SnowyOwlMessage 'Windows Terminal configured.'
