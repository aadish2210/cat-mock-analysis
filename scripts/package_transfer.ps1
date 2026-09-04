param(
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$parent = Split-Path -Parent $root
$stamp = Get-Date -Format "yyyy-MM-dd"
if (-not $OutputPath) {
    $OutputPath = Join-Path $parent "CAT-Strategic-Diagnostic-Vercel-$stamp.zip"
}

$stagingRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cat-portal-package-" + [guid]::NewGuid())
$stagingProject = Join-Path $stagingRoot "cat-mock-analytics"
$excludedDirectories = @(".git", ".vercel", "node_modules", "dist", "__pycache__", ".pytest_cache", ".ruff_cache")
$excludedFiles = @(".env", ".DS_Store")

try {
    New-Item -ItemType Directory -Path $stagingProject -Force | Out-Null
    Get-ChildItem -Path $root -Recurse -File -Force | ForEach-Object {
        $relative = $_.FullName.Substring($root.Length).TrimStart("\", "/")
        $segments = $relative -split "[\\/]"
        if ($segments | Where-Object { $excludedDirectories -contains $_ }) { return }
        if ($excludedFiles -contains $_.Name) { return }
        if ($_.Extension -eq ".zip") { return }
        if ($relative -match "^data[\\/].*\.json$") { return }

        $destination = Join-Path $stagingProject $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $_.FullName -Destination $destination
    }

    $dataDirectory = Join-Path $stagingProject "data"
    New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null
    '{"version":1,"mocks":[]}' | Set-Content -Path (Join-Path $dataDirectory "mocks.json") -Encoding utf8
    '{"version":1,"reviews":{}}' | Set-Content -Path (Join-Path $dataDirectory "review_state.json") -Encoding utf8

    $jwtPattern = 'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
    $secretHits = Get-ChildItem -Path $stagingProject -Recurse -File | Select-String -Pattern $jwtPattern -List -ErrorAction SilentlyContinue
    if ($secretHits) {
        $paths = ($secretHits | ForEach-Object Path) -join ", "
        throw "Packaging stopped: JWT-like content found in $paths"
    }
    if (Test-Path $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    Compress-Archive -Path $stagingProject -DestinationPath $OutputPath -CompressionLevel Optimal
    $archive = Get-Item $OutputPath
    $hash = (Get-FileHash -Path $OutputPath -Algorithm SHA256).Hash
    Write-Host "Created: $($archive.FullName)"
    Write-Host "Size: $([math]::Round($archive.Length / 1MB, 2)) MB"
    Write-Host "SHA256: $hash"
    Write-Host "Source-only Vercel package: no local candidate data, IMS tokens, Supabase keys, caches, or dependencies."
}
finally {
    if (Test-Path $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
}