[CmdletBinding()]
param(
    [string]$ManifestPath
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not $ManifestPath) {
    $ManifestPath = Join-Path $RepositoryRoot 'fonts/manifest.json'
}
if (-not (Test-Path -LiteralPath $ManifestPath)) {
    throw "Font manifest not found: $ManifestPath"
}

function Get-SnowyOwlFontDirectory {
    $UserProfile = [Environment]::GetFolderPath('UserProfile')
    switch (Get-SnowyOwlPlatform) {
        'windows' { return Join-Path $env:LOCALAPPDATA 'Microsoft/Windows/Fonts' }
        'macos' { return Join-Path $UserProfile 'Library/Fonts' }
        default {
            if ($env:XDG_DATA_HOME) {
                return Join-Path $env:XDG_DATA_HOME 'fonts'
            }
            return Join-Path $UserProfile '.local/share/fonts'
        }
    }
}

function Assert-SnowyOwlFontFile {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$ExpectedHash
    )

    $ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
    if ($ActualHash -ine $ExpectedHash) {
        throw "Font checksum mismatch for $(Split-Path $Path -Leaf). Expected $ExpectedHash but received $($ActualHash.ToLowerInvariant())."
    }
}

function Register-SnowyOwlWindowsFont {
    param(
        [Parameter(Mandatory)] [string]$Name,
        [Parameter(Mandatory)] [string]$Path
    )

    $RegistryPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
    New-Item -Path $RegistryPath -Force | Out-Null
    New-ItemProperty -Path $RegistryPath -Name $Name -Value $Path -PropertyType String -Force | Out-Null
}

$Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
$Platform = Get-SnowyOwlPlatform
$DestinationDirectory = Get-SnowyOwlFontDirectory
$TemporaryDirectory = Join-Path ([IO.Path]::GetTempPath()) "snowy-owl-fonts-$([guid]::NewGuid().ToString('N'))"
$InstalledCount = 0

try {
    foreach ($Font in $Manifest.fonts) {
        if (Test-SnowyOwlFontInstalled -Family $Font.family) {
            Write-SnowyOwlMessage "Font already installed: $($Font.family)"
            continue
        }

        New-Item -ItemType Directory -Force -Path $TemporaryDirectory | Out-Null
        New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
        foreach ($File in $Font.files) {
            $TemporaryPath = Join-Path $TemporaryDirectory $File.fileName
            $DestinationPath = Join-Path $DestinationDirectory $File.fileName
            Write-SnowyOwlMessage "Downloading $($Font.family) from Google Fonts."
            Invoke-WebRequest -Uri $File.url -OutFile $TemporaryPath
            Assert-SnowyOwlFontFile -Path $TemporaryPath -ExpectedHash $File.sha256
            Copy-Item -LiteralPath $TemporaryPath -Destination $DestinationPath -Force
            if ($Platform -eq 'windows') {
                Register-SnowyOwlWindowsFont -Name $File.registryName -Path $DestinationPath
            }
            $InstalledCount++
        }
        Write-SnowyOwlMessage "Installed font for current user: $($Font.family)"
    }
}
finally {
    if (Test-Path -LiteralPath $TemporaryDirectory) {
        Remove-Item -LiteralPath $TemporaryDirectory -Recurse -Force
    }
}

if ($InstalledCount -gt 0 -and $Platform -eq 'linux' -and (Get-Command fc-cache -ErrorAction SilentlyContinue)) {
    & fc-cache -f $DestinationDirectory
}
Remove-Variable -Name SnowyOwlInstalledFonts -Scope Script -ErrorAction SilentlyContinue
Write-SnowyOwlMessage "Font setup complete. Installed $InstalledCount file(s); restart open apps to refresh their font lists."
