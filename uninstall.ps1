[CmdletBinding()]
param(
    [ValidateSet('all', 'vscode', 'warp', 'powershell', 'obsidian')]
    [string]$App = 'all',
    [string]$ObsidianVault
)

function Remove-SnowyOwlPowerShell {
    [CmdletBinding()]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseShouldProcessForStateChangingFunctions', '', Justification = 'Internal helper called only by an explicit uninstall operation.')]
    param()

    $Path = $PROFILE.CurrentUserAllHosts
    if (Test-Path $Path) {
        $Text = Get-Content $Path -Raw
        $Pattern = '(?s)' + [regex]::Escape('# >>> Snowy Owl >>>') + '.*?' + [regex]::Escape('# <<< Snowy Owl <<<')
        Set-Content $Path ([regex]::Replace($Text, $Pattern, '').Trim()) -Encoding utf8
    }
}

function Remove-SnowyOwlWarp {
    [CmdletBinding()]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseShouldProcessForStateChangingFunctions', '', Justification = 'Internal helper called only by an explicit uninstall operation.')]
    param()

    $Directories = @(
        "$env:APPDATA\warp-terminal\themes"
        "$env:USERPROFILE\.warp\themes"
        "$HOME/.local/share/warp-terminal/themes"
        "$HOME/.warp/themes"
    )
    foreach ($Directory in $Directories) {
        if (Test-Path $Directory) {
            Remove-Item "$Directory/snowy-owl-*.yaml" -Force -ErrorAction SilentlyContinue
        }
    }
}

function Remove-SnowyOwlObsidian {
    [CmdletBinding()]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseShouldProcessForStateChangingFunctions', '', Justification = 'Internal helper called only by an explicit uninstall operation.')]
    param(
        [string]$VaultPath
    )

    if ($VaultPath) {
        $Path = Join-Path $VaultPath '.obsidian/snippets/snowy-owl.css'
        Remove-Item $Path -Force -ErrorAction SilentlyContinue
    }
}

function Remove-SnowyOwlVSCode {
    [CmdletBinding()]
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseShouldProcessForStateChangingFunctions', '', Justification = 'Internal helper called only by an explicit uninstall operation.')]
    param()

    if (Get-Command code -ErrorAction SilentlyContinue) {
        & code --uninstall-extension snowy-owl-local.snowy-owl
    }
}

$Targets = if ($App -eq 'all') {
    @('vscode', 'warp', 'powershell', 'obsidian')
}
else {
    @($App)
}

foreach ($Target in $Targets) {
    switch ($Target) {
        'vscode' { Remove-SnowyOwlVSCode }
        'warp' { Remove-SnowyOwlWarp }
        'powershell' { Remove-SnowyOwlPowerShell }
        'obsidian' { Remove-SnowyOwlObsidian -VaultPath $ObsidianVault }
    }
}

Write-Output '[Snowy Owl] Removed Snowy Owl-owned files/blocks where safely supported. Windows Terminal backup can be restored manually.'
