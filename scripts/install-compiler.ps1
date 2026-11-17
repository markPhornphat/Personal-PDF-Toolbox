param([string]$Directory = (Join-Path $PSScriptRoot '..\artifacts\Inno Setup'))
$ErrorActionPreference = 'Stop'
$Directory = [System.IO.Path]::GetFullPath($Directory)
$installer = Join-Path (Split-Path $Directory) 'innosetup-6.7.3.exe'
New-Item -ItemType Directory -Force (Split-Path $Directory) | Out-Null
Invoke-WebRequest 'https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe' -OutFile $installer
$expected = '9C73C3BAE7ED48D44112A0F48E66742C00090BDB5BEF71D9D3C056C66E97B732'
if ((Get-FileHash $installer -Algorithm SHA256).Hash -ne $expected) {
    throw 'Inno Setup compiler checksum mismatch'
}
$process = Start-Process -FilePath $installer -ArgumentList @(
    '/VERYSILENT', '/CURRENTUSER', '/SUPPRESSMSGBOXES', '/NORESTART', ('/DIR="' + $Directory + '"')
) -WindowStyle Hidden -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Inno Setup compiler exited with $($process.ExitCode)" }
