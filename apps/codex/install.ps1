[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$RepositoryRoot,
    [hashtable]$Options = @{}
)

$ErrorActionPreference = 'Stop'
. (Join-Path $RepositoryRoot 'scripts/install-common.ps1')

if (-not (Test-SnowyOwlPlatform -App codex -RepositoryRoot $RepositoryRoot)) {
    return
}

$SourcePath = Join-Path $RepositoryRoot 'generated/codex/snowy-owl-desktop.toml'
if (-not (Test-Path -LiteralPath $SourcePath)) {
    Write-SnowyOwlMessage 'Generated Codex theme not found. Run scripts/build.ps1 -All, then retry.'
    return
}

$CodexHomePath = if ($env:CODEX_HOME) {
    $env:CODEX_HOME
}
else {
    Join-Path $HOME '.codex'
}
$ConfigPath = Join-Path $CodexHomePath 'config.toml'
New-Item -ItemType Directory -Force -Path $CodexHomePath | Out-Null
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    New-Item -ItemType File -Path $ConfigPath | Out-Null
}
Backup-SnowyOwlFile $ConfigPath

$SourceText = Get-Content -Raw -LiteralPath $SourcePath
$ManifestPath = Join-Path $RepositoryRoot 'generated/font-selections.json'
if (Test-Path -LiteralPath $ManifestPath) {
    $FontManifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
    foreach ($Role in 'ui', 'monospace') {
        $DefaultFont = $FontManifest.codex.$Role
        $InstalledFont = Get-SnowyOwlFontSelection -RepositoryRoot $RepositoryRoot -App codex -Role $Role
        if ($InstalledFont) {
            foreach ($Property in 'family', 'fullName', 'postScriptName') {
                $OldValue = $DefaultFont.$Property
                $NewValue = $InstalledFont.$Property
                if ($OldValue -and $NewValue) {
                    $SourceText = $SourceText.Replace("`"$OldValue`"", "`"$NewValue`"")
                }
            }
        }
    }
}

$TemplateSections = [ordered]@{}
$CurrentSection = $null
foreach ($Line in ($SourceText -split '\r?\n')) {
    if ($Line -match '^\s*\[([^\]]+)\]\s*$') {
        $CurrentSection = $Matches[1]
        $TemplateSections[$CurrentSection] = [ordered]@{}
    }
    elseif ($CurrentSection -and $Line -match '^\s*([A-Za-z0-9_-]+)\s*=\s*(.+?)\s*$') {
        $TemplateSections[$CurrentSection][$Matches[1]] = $Matches[2]
    }
}

$RawContent = [IO.File]::ReadAllText($ConfigPath)
$NewLine = if ($RawContent.Contains("`r`n")) { "`r`n" } else { "`n" }
$HadFinalNewLine = $RawContent.EndsWith("`n")
$Lines = if ($RawContent) { @($RawContent -split '\r?\n') } else { @() }
if ($HadFinalNewLine -and $Lines.Count -gt 0 -and $Lines[-1] -eq '') {
    $Lines = @($Lines[0..($Lines.Count - 2)])
}

$Output = [System.Collections.Generic.List[string]]::new()
$SeenSections = @{}
$SeenKeys = @{}
$CurrentSection = $null
$AddMissingKeys = {
    param([string]$Section)

    if (-not $Section -or -not $TemplateSections.Contains($Section)) {
        return
    }
    foreach ($Entry in $TemplateSections[$Section].GetEnumerator()) {
        $Identity = "$Section`n$($Entry.Key)"
        if (-not $SeenKeys.ContainsKey($Identity)) {
            $Output.Add("$($Entry.Key) = $($Entry.Value)")
            $SeenKeys[$Identity] = $true
        }
    }
}

foreach ($Line in $Lines) {
    if ($Line -match '^\s*\[([^\]]+)\]\s*(?:#.*)?$') {
        & $AddMissingKeys $CurrentSection
        $CurrentSection = $Matches[1]
        if ($TemplateSections.Contains($CurrentSection)) {
            $SeenSections[$CurrentSection] = $true
        }
        $Output.Add($Line)
        continue
    }

    if (
        $CurrentSection -and
        $TemplateSections.Contains($CurrentSection) -and
        $Line -match '^(\s*([A-Za-z0-9_-]+)\s*=\s*)(.*?)(\s+#.*)?$'
    ) {
        $Key = $Matches[2]
        if ($TemplateSections[$CurrentSection].Contains($Key)) {
            $Identity = "$CurrentSection`n$Key"
            $Comment = $Matches[4]
            $Output.Add($Matches[1] + $TemplateSections[$CurrentSection][$Key] + $Comment)
            $SeenKeys[$Identity] = $true
            continue
        }
    }
    $Output.Add($Line)
}
& $AddMissingKeys $CurrentSection

foreach ($Section in $TemplateSections.Keys) {
    if ($SeenSections.ContainsKey($Section)) {
        continue
    }
    if ($Output.Count -gt 0 -and $Output[-1] -ne '') {
        $Output.Add('')
    }
    $Output.Add("[$Section]")
    foreach ($Entry in $TemplateSections[$Section].GetEnumerator()) {
        $Output.Add("$($Entry.Key) = $($Entry.Value)")
    }
}

$Content = $Output -join $NewLine
if ($HadFinalNewLine -or -not $RawContent) {
    $Content += $NewLine
}
[IO.File]::WriteAllText($ConfigPath, $Content, [Text.UTF8Encoding]::new($false))
Write-SnowyOwlMessage "Codex desktop theme configured: $ConfigPath"
Write-SnowyOwlMessage 'Restart Codex to apply the theme.'
