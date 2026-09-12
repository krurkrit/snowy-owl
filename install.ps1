[CmdletBinding()]
param(
    [string]$App = 'all',
    [string]$ObsidianVault,
    [switch]$InstallFonts,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
. (Join-Path $Root 'scripts/install-common.ps1')

if ($InstallFonts) {
    & (Join-Path $Root 'scripts/install-fonts.ps1')
}

$Installers = @{}
Get-ChildItem -Path (Join-Path $Root 'apps') -Directory | ForEach-Object {
    $InstallerPath = Join-Path $_.FullName 'install.ps1'
    if (Test-Path -LiteralPath $InstallerPath) {
        $Installers[$_.Name] = $InstallerPath
    }
}

if ($Check) {
    Write-SnowyOwlMessage "Version $(Get-Content (Join-Path $Root 'VERSION'))"
    Write-SnowyOwlMessage "Operating system: $(Get-SnowyOwlPlatform)"
    Write-SnowyOwlMessage "App installers: $($Installers.Keys.Count) found"
    foreach ($Command in 'code', 'pwsh', 'warp') {
        $InstalledCommand = Get-Command $Command -ErrorAction SilentlyContinue
        $Status = if ($InstalledCommand) { 'found' } else { 'not found' }
        Write-SnowyOwlMessage "${Command}: $Status"
    }
    foreach ($Font in 'Inter', 'Noto Sans', 'JetBrains Mono', 'Cascadia Mono', 'Consolas') {
        $Status = if (Test-SnowyOwlFontInstalled -Family $Font) { 'found' } else { 'not found' }
        Write-SnowyOwlMessage "Font ${Font}: $Status"
    }
    exit
}

$Targets = if ($App -eq 'all') {
    @($Installers.Keys | Sort-Object)
}
else {
    @($App)
}

$Options = @{
    ObsidianVault = $ObsidianVault
}
foreach ($Target in $Targets) {
    if (-not $Installers.ContainsKey($Target)) {
        $Available = @('all') + @($Installers.Keys | Sort-Object)
        throw "Unknown app '$Target'. Available values: $($Available -join ', ')"
    }
    & $Installers[$Target] -RepositoryRoot $Root -Options $Options
}
