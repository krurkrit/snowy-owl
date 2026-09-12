[CmdletBinding()]
param(
    [switch]$Html,
    [switch]$SkipValidation
)

$ErrorActionPreference = 'Stop'
$RepositoryRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if ($SkipValidation -and -not $Html) {
    Write-Error '-SkipValidation requires -Html because it is only for dashboard debugging.'
    exit 2
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

$ContrastArguments = @("$RepositoryRoot/scripts/validate_contrast.py")
if (-not $SkipValidation) {
    $ContrastArguments += '--markdown'
}
if ($Html) {
    $ContrastArguments += '--html'
}
if ($SkipValidation) {
    $ContrastArguments += '--skip-validation'
}

Invoke-PythonCommand -PythonArguments $ContrastArguments
if (-not $SkipValidation) {
    Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/validate_fonts.py"
}
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/generate_token_docs.py"
Invoke-PythonCommand -PythonArguments "$RepositoryRoot/scripts/generate_preview.py"
Write-Output '[Snowy Owl] Documentation updated.'
