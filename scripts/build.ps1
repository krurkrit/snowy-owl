[CmdletBinding()]
param(
    [switch]$All,
    [switch]$Html
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($All) {
    Write-Verbose 'Running all build steps.'
}

function Invoke-PythonCommand {
    param(
        [Parameter(Mandatory)]
        [string[]]$PythonArguments
    )

    & python @PythonArguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Invoke-PythonCommand -PythonArguments @(
    '-m',
    'unittest',
    'discover',
    '-s',
    "$RepositoryRoot/tests"
)
$ContrastArguments = @("$RepositoryRoot/scripts/validate_contrast.py")
if ($Html) {
    $ContrastArguments += '--html'
}
Invoke-PythonCommand -PythonArguments $ContrastArguments
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/validate_fonts.py"
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/generate_token_docs.py"
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/generate.py"
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/check_generated.py"
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/generate_preview.py"
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/package_vscode.py"
Write-Output '[Snowy Owl] Build complete.'
