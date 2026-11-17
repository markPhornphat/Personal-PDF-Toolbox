param(
    [string]$Installer = (Join-Path $PSScriptRoot '..\dist\PDF-Toolbox-Setup-x64.exe'),
    [string]$PreviousInstaller,
    [ValidateSet('offscreen', 'windows')][string]$Platform = 'offscreen',
    [ValidateSet('english', 'thai')][string]$Language = 'english'
)
$ErrorActionPreference = 'Stop'
$installer = (Resolve-Path -LiteralPath $Installer).Path
$registryKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{400F60D3-F378-465A-9E76-4C1F12DF7C10}_is1'
if (Test-Path -LiteralPath $registryKey) {
    throw 'Run the installer smoke test in a Windows user profile without PDF Toolbox installed.'
}
$testRoot = Join-Path $PSScriptRoot '..\artifacts'
New-Item -ItemType Directory -Force $testRoot | Out-Null
$target = Join-Path (Resolve-Path $testRoot) ('install-smoke-' + [guid]::NewGuid().ToString('N'))
$env:QT_QPA_PLATFORM = $Platform
function Invoke-SmokeProcess($File, $Arguments, $Timeout = 60000) {
    $process = Start-Process -FilePath $File -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $process.WaitForExit($Timeout)) {
        Stop-Process -Id $process.Id -ErrorAction SilentlyContinue
        throw "Timed out running $File"
    }
    if ($process.ExitCode -ne 0) { throw "$File exited with $($process.ExitCode)" }
}
$setupArguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS',
    ('/DIR="' + $target + '"'))
$initialInstaller = if ($PreviousInstaller) {
    (Resolve-Path -LiteralPath $PreviousInstaller).Path
} else {
    $installer
}
Invoke-SmokeProcess $initialInstaller ($setupArguments + ('/LOG="' + $target + '.log"'))
$app = Join-Path $target 'PDF Toolbox.exe'
$env:Path = "$env:SystemRoot\System32;$env:SystemRoot"
Invoke-SmokeProcess $app '--smoke-test'
$initialVersion = (Get-Item -LiteralPath $app).VersionInfo.ProductVersion.Trim()
$document = Join-Path $target '_internal\keep-me.pdf'
'%PDF-1.7 smoke fixture' | Set-Content -LiteralPath $document
Invoke-SmokeProcess $installer ($setupArguments + "/LANG=$Language" + ('/LOG="' + $target + '-upgrade.log"'))
if (-not (Test-Path -LiteralPath $document)) { throw 'Reinstallation removed a user file' }
Invoke-SmokeProcess $app '--smoke-test'
$updatedVersion = (Get-Item -LiteralPath $app).VersionInfo.ProductVersion.Trim()
if ($PreviousInstaller -and ([version]$updatedVersion -le [version]$initialVersion)) {
    throw "Upgrade did not install a newer version ($initialVersion to $updatedVersion)"
}
Invoke-SmokeProcess (Join-Path $target 'unins000.exe') @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART')
$deadline = [DateTime]::UtcNow.AddSeconds(10)
while ((Test-Path -LiteralPath $app) -or (Test-Path -LiteralPath $registryKey)) {
    if ([DateTime]::UtcNow -ge $deadline) {
        throw 'Uninstaller did not finish removing the application and its registration'
    }
    Start-Sleep -Milliseconds 100
}
if (-not (Test-Path -LiteralPath $document)) { throw 'Uninstallation removed a user file' }
Write-Output "Per-user install, bundled startup, $initialVersion to $updatedVersion, uninstall and user-file preservation passed."
