[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App powershell -RepositoryRoot $RepositoryRoot)) {
    return
}

$ProfilePath = $PROFILE.CurrentUserAllHosts
New-Item -ItemType Directory -Force -Path (Split-Path $ProfilePath) | Out-Null
if (-not (Test-Path -LiteralPath $ProfilePath)) {
    New-Item -ItemType File -Path $ProfilePath | Out-Null
}
Backup-SnowyOwlFile $ProfilePath

$Text = Get-Content -Raw -LiteralPath $ProfilePath
$BeginMarker = '# >>> Snowy Owl >>>'
$EndMarker = '# <<< Snowy Owl <<<'
$Pattern = '(?s)' + [regex]::Escape($BeginMarker) + '.*?' + [regex]::Escape($EndMarker)
$Text = [regex]::Replace($Text, $Pattern, '').TrimEnd()
$SourcePath = Join-Path $RepositoryRoot 'generated/powershell/snowy-owl.ps1'
$Block = Get-Content -Raw -LiteralPath $SourcePath
$NewLine = [Environment]::NewLine
$Content = $Text + $NewLine + $NewLine + $BeginMarker + $NewLine + $Block + $EndMarker + $NewLine
Set-Content -LiteralPath $ProfilePath -Value $Content -Encoding utf8
Write-SnowyOwlMessage "PowerShell profile updated: $ProfilePath"
