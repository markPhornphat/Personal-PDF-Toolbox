param([string]$Installer = (Join-Path $PSScriptRoot '..\dist\PDF-Toolbox-Setup-x64.exe'))
$ErrorActionPreference = 'Stop'
$installer = (Resolve-Path -LiteralPath $Installer).Path
$registryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{400F60D3-F378-465A-9E76-4C1F12DF7C10}_is1'
if (Test-Path -LiteralPath $registryKey) {
    throw 'Run the installer smoke test in a Windows user profile without PDF Toolbox installed.'
}
$testRoot = Join-Path $PSScriptRoot '..\artifacts'
New-Item -ItemType Directory -Force $testRoot | Out-Null
$target = Join-Path (Resolve-Path $testRoot) ('install-smoke-' + [guid]::NewGuid().ToString('N'))
$env:QT_QPA_PLATFORM = 'offscreen'
function Invoke-SmokeProcess($File, $Arguments, $Timeout = 60000) {
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($Timeout)) {
        Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        throw "Timed out running $File"
    }
    if ($process.ExitCode -ne 0) { throw "$File exited with $($process.ExitCode)" }
}
Invoke-SmokeProcess $installer @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
    ('/DIR="' + $target + '"'), ('/LOG="' + $target + '.log"'))
$app = Join-Path $target 'PDF Toolbox.exe'
$env:Path = "$env:SystemRoot\System32;$env:SystemRoot"
Invoke-SmokeProcess $app '--smoke-test'
$document = Join-Path $target '_internal\keep-me.pdf'
'%PDF-1.7 smoke fixture' | Set-Content -LiteralPath $document
Invoke-SmokeProcess $installer @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
    ('/DIR="' + $target + '"'))
if (-not (Test-Path -LiteralPath $document)) { throw 'Reinstallation removed a user file' }
Invoke-SmokeProcess (Join-Path $target 'unins000.exe') @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
Wait-Process -Name unins000 -Timeout 10 -ErrorAction SilentlyContinue
if (Test-Path -LiteralPath $app) { throw 'Uninstaller did not remove the application' }
if (-not (Test-Path -LiteralPath $document)) { throw 'Uninstallation removed a user file' }
Write-Output 'Per-user install, bundled startup, reinstallation, uninstall and user-file preservation passed.'
