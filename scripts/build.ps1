param([string]$Compiler = (Join-Path $PSScriptRoot '..\artifacts\Inno Setup\ISCC.exe'))
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $root
try {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    $version = & $python scripts/build_metadata.py
    if ($LASTEXITCODE -ne 0) { throw 'Metadata generation failed' }
    & $python -m PyInstaller --noconfirm packaging/pdf-toolbox.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    $bundle = Join-Path $root 'dist\PDF Toolbox'
    $program = Join-Path $bundle 'PDF Toolbox.exe'
    $startup = Start-Process -FilePath $program -ArgumentList '--smoke-test' -WindowStyle Hidden -PassThru
    if (-not $startup.WaitForExit(30000)) {
        Stop-Process -Id $startup.Id -ErrorAction SilentlyContinue
        throw 'Packaged application startup timed out'
    }
    if ($startup.ExitCode -ne 0) {
        $diagnostic = Join-Path $bundle 'pdf-toolbox-smoke-error.txt'
        if (Test-Path $diagnostic) { Get-Content $diagnostic }
        throw "Packaged application exited with $($startup.ExitCode)"
    }
    Get-ChildItem -LiteralPath $bundle -Recurse -File |
        ForEach-Object { [IO.Path]::GetRelativePath($bundle, $_.FullName) } |
        Set-Content -Encoding ascii (Join-Path $bundle '.bundle-files.txt')
    & $Compiler "/DAppVersion=$version" "/DBundleDir=$bundle" 'installer/pdf-toolbox.iss'
    if ($LASTEXITCODE -ne 0) { throw 'Inno Setup failed' }
    $installer = Join-Path $root 'dist\PDF-Toolbox-Setup-x64.exe'
    $checksum = (Get-FileHash $installer -Algorithm SHA256).Hash.ToLowerInvariant()
    "$checksum  PDF-Toolbox-Setup-x64.exe" | Set-Content -Encoding ascii dist/SHA256SUMS.txt
    $configuration = Get-Content build/metadata/update-config.json -Raw -ErrorAction SilentlyContinue
    if (-not $configuration) { $configuration = '{}' }
    @{ version = $version; config = ($configuration | ConvertFrom-Json) } |
        ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 dist/release-build.json
} finally {
    Pop-Location
}
