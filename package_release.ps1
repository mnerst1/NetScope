param([string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath 'dist\NetScope\NetScope.exe')) { throw 'Build onedir first' }
New-Item -ItemType Directory -Force -Path release | Out-Null
Copy-Item -LiteralPath README.md,PRIVACY.md,INSTALL_RU.md,LICENSE,THIRD_PARTY.md,TEST_CHECKLIST.md,VERIFICATION.md,RELEASE_NOTES.md -Destination dist\NetScope
Copy-Item -LiteralPath third_party_licenses -Destination dist\NetScope -Recurse -Force
Compress-Archive -Path dist\NetScope -DestinationPath release\NetScope-v1.0.0-Windows-x64.zip -Force
Write-Host 'release\NetScope-v1.0.0-Windows-x64.zip'
