param([switch]$OneFile, [string]$Python = '.\.venv\Scripts\python.exe')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath $Python)) { throw 'Create .venv and install requirements.txt first. See BUILD_EXE_RU.md.' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
if ($OneFile) {
    & $Python -m PyInstaller --noconfirm --clean --noupx --windowed --onefile --name NetScope-OneFile --icon netscope\assets\netscope.ico --add-data 'netscope\assets;netscope\assets' --add-data 'netscope\i18n\locales;netscope\i18n\locales' main.py
} else {
    & $Python -m PyInstaller --noconfirm --clean NetScope.spec
}
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
$Executable = if ($OneFile) { 'dist\NetScope-OneFile.exe' } else { 'dist\NetScope\NetScope.exe' }
$SmokeDir = Join-Path $PSScriptRoot 'build\smoke'
$Process = Start-Process -FilePath (Resolve-Path -LiteralPath $Executable) -ArgumentList '--smoke-test', '--data-dir', ('"' + $SmokeDir + '"') -WindowStyle Hidden -PassThru
if (-not $Process.WaitForExit(30000)) { $Process.Kill(); throw 'EXE startup timed out' }
if ($Process.ExitCode -ne 0) { throw "EXE smoke test failed: $($Process.ExitCode)" }
Write-Host "Built and startup-tested: $Executable"
