function Write-SnowyOwlMessage {
    param(
        [Parameter(Mandatory)]
        [string]$Message
    )

    Write-Information "[Snowy Owl] $Message" -InformationAction Continue
}

function Backup-SnowyOwlFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    if (Test-Path -LiteralPath $Path) {
        $BackupPath = "$Path.snowy-owl.bak"
        Copy-Item -LiteralPath $Path -Destination $BackupPath -Force
        Write-SnowyOwlMessage "Backup: $BackupPath"
    }
}

function Get-SnowyOwlPlatform {
    if ([Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
            [Runtime.InteropServices.OSPlatform]::Windows)) {
        return 'windows'
    }
    if ([Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
            [Runtime.InteropServices.OSPlatform]::OSX)) {
        return 'macos'
    }
    return 'linux'
}

function Test-SnowyOwlPlatform {
    param(
        [Parameter(Mandatory)]
        [string]$App,
        [Parameter(Mandatory)]
        [string]$RepositoryRoot
    )

    $Platform = Get-SnowyOwlPlatform
    $RegistryPath = Join-Path $RepositoryRoot 'generated/apps.json'
    if (-not (Test-Path -LiteralPath $RegistryPath)) {
        Write-Warning '[Snowy Owl] App registry not found; run scripts/build.ps1 -All.'
        return $false
    }
    $Registry = Get-Content -Raw -LiteralPath $RegistryPath | ConvertFrom-Json
    $Configuration = $Registry.$App
    if (-not $Configuration) {
        throw "Unknown app '$App' in generated app registry."
    }
    $Supported = @($Configuration.supportedOperatingSystems)
    if ($Platform -in $Supported) {
        return $true
    }
    Write-SnowyOwlMessage "$($Configuration.name) personalization is unsupported on $Platform. Supported: $($Supported -join ', ')."
    return $false
}

function Get-SnowyOwlInstalledFontNames {
    if (Get-Variable -Name SnowyOwlInstalledFonts -Scope Script -ErrorAction SilentlyContinue) {
        return $script:SnowyOwlInstalledFonts
    }

    $Names = [System.Collections.Generic.List[string]]::new()
    $Platform = Get-SnowyOwlPlatform
    if ($Platform -eq 'windows') {
        foreach ($RegistryPath in @(
                'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts',
                'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts')) {
            if (Test-Path -LiteralPath $RegistryPath) {
                $Properties = Get-ItemProperty -LiteralPath $RegistryPath
                $Properties.PSObject.Properties |
                    Where-Object Name -NotLike 'PS*' |
                    ForEach-Object { $Names.Add($_.Name); $Names.Add([string]$_.Value) }
            }
        }
    }
    elseif ($Platform -eq 'linux' -and (Get-Command fc-list -ErrorAction SilentlyContinue)) {
        & fc-list --format='%{family}\n' | ForEach-Object { $Names.Add($_) }
    }
    else {
        foreach ($Directory in @(
                (Join-Path $HOME 'Library/Fonts'),
                '/Library/Fonts',
                '/System/Library/Fonts')) {
            if (Test-Path -LiteralPath $Directory) {
                Get-ChildItem -LiteralPath $Directory -File -Recurse -ErrorAction SilentlyContinue |
                    ForEach-Object { $Names.Add($_.BaseName) }
            }
        }
    }
    $script:SnowyOwlInstalledFonts = @($Names)
    return $script:SnowyOwlInstalledFonts
}

function Test-SnowyOwlFontInstalled {
    param(
        [Parameter(Mandatory)]
        [string]$Family
    )

    if ($Family -in @('sans-serif', 'monospace', 'system-ui')) {
        return $false
    }
    $Needle = ($Family -replace '[^A-Za-z0-9]', '').ToLowerInvariant()
    foreach ($Name in (Get-SnowyOwlInstalledFontNames)) {
        $Candidate = ([string]$Name -replace '[^A-Za-z0-9]', '').ToLowerInvariant()
        if ($Candidate.Contains($Needle)) {
            return $true
        }
    }
    return $false
}

function Select-SnowyOwlFontCandidate {
    param(
        [Parameter(Mandatory)]
        [string]$App,
        [Parameter(Mandatory)]
        [string]$Role,
        [Parameter(Mandatory)]
        [object[]]$Candidates
    )

    foreach ($Candidate in $Candidates) {
        if (Test-SnowyOwlFontInstalled -Family $Candidate.family) {
            if ($Candidate -ne $Candidates[0]) {
                Write-SnowyOwlMessage "$App $Role font fallback: $($Candidate.family)."
            }
            return $Candidate
        }
    }
    $Families = @(
        $Candidates.family |
            Where-Object { $_ -notin @('sans-serif', 'monospace', 'system-ui') }
    )
    Write-Warning "[Snowy Owl] $App needs a $Role font. Install one of: $($Families -join ', '). Personalization will continue with the app or system fallback."
    return $null
}

function Get-SnowyOwlFontSelection {
    param(
        [Parameter(Mandatory)]
        [string]$RepositoryRoot,
        [Parameter(Mandatory)]
        [string]$App,
        [Parameter(Mandatory)]
        [string]$Role
    )

    $ManifestPath = Join-Path $RepositoryRoot 'generated/font-selections.json'
    if (-not (Test-Path -LiteralPath $ManifestPath)) {
        Write-Warning '[Snowy Owl] Font manifest not found; run scripts/build.ps1 -All.'
        return $null
    }
    $Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
    $Selection = $Manifest.$App.$Role
    if (-not $Selection -or $Selection.mode -eq 'unsupported') {
        return $null
    }
    return Select-SnowyOwlFontCandidate -App $App -Role $Role -Candidates @($Selection.candidates)
}
