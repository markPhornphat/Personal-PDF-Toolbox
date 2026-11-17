$ErrorActionPreference = 'Stop'
$python = '.venv/Scripts/python.exe'
$releaseRepo = $env:PDF_TOOLBOX_RELEASE_REPOSITORY
if ($releaseRepo -notmatch '^[a-zA-Z0-9-]+/[a-zA-Z0-9_.-]+$') {
    throw 'Set a valid owner/repository release destination.'
}
if (-not $env:PDF_TOOLBOX_UPDATE_PUBLIC_KEY -or -not $env:PDF_TOOLBOX_SIGNING_KEY) {
    throw 'Configure the release verification key and signing secret before publication.'
}
$version = & $python scripts/build_metadata.py
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') {
    throw 'Invalid stable application version'
}
$tag = 'v' + $version
$headers = @{
    Authorization = "Bearer $env:GH_TOKEN"
    Accept = 'application/vnd.github+json'
    'X-GitHub-Api-Version' = '2022-11-28'
}
$endpoint = "https://api.github.com/repos/$releaseRepo"
$null = Invoke-RestMethod -Uri $endpoint -Headers $headers
$latest = Invoke-RestMethod -Uri "$endpoint/releases/latest" -Headers $headers -SkipHttpErrorCheck -StatusCodeVariable status
if ($status -eq 200) {
    if ($latest.tag_name -notmatch '^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$') {
        throw 'Latest stable tag is not a valid release version'
    }
    if ([version]$version -le [version]($latest.tag_name.Substring(1))) {
        Write-Output "Stable release already at $($latest.tag_name) or higher."
        exit 0
    }
} elseif ($status -ne 404) {
    throw "Latest release lookup failed with HTTP $status"
}
$null = Invoke-RestMethod -Uri "$endpoint/releases/tags/$tag" -Headers $headers -SkipHttpErrorCheck -StatusCodeVariable status
if ($status -ne 404) { throw "Tag lookup did not confirm a new release version (HTTP $status)" }
$null = Invoke-RestMethod -Uri "$endpoint/git/ref/tags/$tag" -Headers $headers -SkipHttpErrorCheck -StatusCodeVariable status
if ($status -ne 404) { throw "Git tag lookup did not confirm a new tag (HTTP $status)" }

$files = @(
    'release-assets/PDF-Toolbox-Setup-x64.exe',
    'release-assets/SHA256SUMS.txt',
    'release-assets/update-manifest.json',
    'release-assets/update-manifest.sig'
)
$expected = (Get-Content -LiteralPath $files[1] -Raw).Split(' ')[0]
if ((Get-FileHash -LiteralPath $files[0] -Algorithm SHA256).Hash -ne $expected) {
    throw 'The downloaded build artifact failed its checksum.'
}
& $python scripts/sign_release.py release-assets
if ($LASTEXITCODE -ne 0) { throw 'Release signing failed' }
$notes = Select-String -LiteralPath CHANGELOG.md -SimpleMatch "## $version"
if (-not $notes) { throw 'Add matching release notes to CHANGELOG.md.' }
$target = if ($releaseRepo -eq $env:PDF_TOOLBOX_SOURCE_REPOSITORY) { $env:GITHUB_SHA } else {
    $repo = Invoke-RestMethod -Uri $endpoint -Headers $headers
    $repo.default_branch
}
gh release create $tag @files --repo $releaseRepo --target $target --draft --title "PDF Toolbox $version" --notes-file CHANGELOG.md
if ($LASTEXITCODE -ne 0) { throw 'Draft creation or upload failed' }
gh release edit $tag --repo $releaseRepo --draft=false --latest
if ($LASTEXITCODE -ne 0) { throw 'Publishing the verified draft failed' }
