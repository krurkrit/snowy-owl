[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App slack -RepositoryRoot $RepositoryRoot)) {
    return
}

$Theme = '#F8F9FA,#F1F3F5,#1450A0,#FFFFFF,#18191B,#1450A0,#12633D,#A52834,#FFC107,#18191B'
if (Get-Command Set-Clipboard -ErrorAction SilentlyContinue) {
    Set-Clipboard $Theme
    Write-SnowyOwlMessage 'Slack theme string copied to clipboard.'
}
else {
    Write-SnowyOwlMessage "Slack theme: $Theme"
}
Write-SnowyOwlMessage 'Slack: Preferences > Appearance > Custom theme > Import theme.'
