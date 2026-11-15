# =========================================================================
# Copyright (C) 2026 Ezequiel M. Rezende
# License: GPL-3.0-or-later (same as IngeTrazo)
# =========================================================================
# Build the distributable igz_tb_scenes.zip for the IngeTrazo extension
# catalog (https://github.com/ingelibre/ingetrazo-extensions).
#
# Windows / PowerShell builder — no Python needed. It produces the SAME
# archive layout as packaging/build_extension.py (one top-level folder,
# igz_tb_scenes/, holding __init__.py, core/, i18n/, icons/ and the docs).
#
# The catalog installs ONE file per entry: a .py file, or a .zip holding a
# single folder with an __init__.py (see TEMPLATE.toml in that repository).
#
# Fixed entry timestamps keep the archive stable: rebuilding it prints the
# same SHA-256 as long as the content is unchanged. That SHA-256 is the
# value pasted into extensions/igz_tb_scenes.toml, and must match the file
# uploaded as the GitHub Release asset of the tag named in `download`.
#
# Usage:
#     powershell -ExecutionPolicy Bypass -File packaging\build_extension.ps1
#
# Output:
#     dist/igz_tb_scenes.zip
#     dist/igz_tb_scenes.zip.sha256
#
# Note: when ``python`` is on PATH this script delegates to
# build_extension.py, so both produce the same SHA-256. The pure-PowerShell
# path (IGZ_BUILD_NO_PYTHON=1) builds the same tree but not the same bytes.
# =========================================================================
[CmdletBinding()]
param(
    [string]$Output
)

$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }

# When Python is available, hand over to packaging/build_extension.py so both
# builders emit byte-identical archives (same SHA-256) — the catalog entry must
# match the released asset exactly. Set IGZ_BUILD_NO_PYTHON=1 to force the
# pure-PowerShell path (same tree, but a different byte stream).
if (-not $Output -and -not $env:IGZ_BUILD_NO_PYTHON) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command py -ErrorAction SilentlyContinue }
    if ($py) {
        & $py.Source (Join-Path $scriptDir 'build_extension.py')
        exit $LASTEXITCODE
    }
}

if (-not $Output) { $Output = Join-Path $scriptDir '..\dist' }

$root = (Resolve-Path (Join-Path $scriptDir '..')).Path
$package = 'igz_tb_scenes'
$zipName = "$package.zip"

# Fixed timestamp -> reproducible archive.
$fixed = [System.DateTimeOffset]::new(2026, 1, 1, 0, 0, 0, [System.TimeSpan]::Zero)

$outDir = [System.IO.Path]::GetFullPath($Output)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$zipPath = Join-Path $outDir $zipName
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }

# --- Collect the files, then sort by archive path --------------------------
$packageDir = Join-Path $root $package
$entries = @{}

function Add-Entry([string]$arc, [string]$src) {
    if (-not (Test-Path -LiteralPath $src -PathType Leaf)) { return }
    if (-not $entries.ContainsKey($arc)) {
        $entries[$arc] = [pscustomobject]@{ Arc = $arc; Src = $src }
    }
}

# The whole package tree: __init__.py, core/*.py, i18n/*.json, icons/*.svg.
$excludedDirs = @('__pycache__', '.git', '.mypy_cache', '.pytest_cache')
Get-ChildItem -LiteralPath $packageDir -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($packageDir.Length).TrimStart('\', '/').Replace('\', '/')
    $parts = $rel.Split('/')
    if ($parts | Where-Object { $excludedDirs -contains $_ }) { return }
    if ($_.Name -in @('Thumbs.db', 'Desktop.ini', '.DS_Store')) { return }
    if ($_.Extension -in @('.pyc', '.pyo', '.pyd')) { return }
    Add-Entry "$package/$rel" $_.FullName
}

# Docs stay at the repository root but ship inside the package folder.
foreach ($f in @('LICENSE', 'README.md', 'README_ptBR.md', 'THIRD-PARTY.md')) {
    Add-Entry "$package/$f" (Join-Path $root $f)
}

$sorted = $entries.Values | Sort-Object Arc

# Text entries are normalised to LF so the fingerprint does not depend on the
# Git line-ending settings of the machine that builds the archive.
function ConvertTo-Lf([byte[]]$bytes) {
    $out = New-Object System.Collections.Generic.List[byte]($bytes.Length)
    for ($i = 0; $i -lt $bytes.Length; $i++) {
        if ($bytes[$i] -eq 13 -and ($i + 1) -lt $bytes.Length -and $bytes[$i + 1] -eq 10) {
            continue
        }
        $out.Add($bytes[$i])
    }
    return ,$out.ToArray()
}

# --- Write the zip ---------------------------------------------------------
$stream = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::CreateNew)
try {
    $archive = New-Object System.IO.Compression.ZipArchive(
        $stream, [System.IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($e in $sorted) {
            $entry = $archive.CreateEntry(
                $e.Arc, [System.IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $fixed
            $dest = $entry.Open()
            try {
                $bytes = [System.IO.File]::ReadAllBytes($e.Src)
                if ($e.Src -match '\.(py|md|json|svg|txt)$') {
                    $bytes = ConvertTo-Lf $bytes
                }
                $dest.Write($bytes, 0, $bytes.Length)
            } finally {
                $dest.Dispose()
            }
        }
    } finally {
        $archive.Dispose()
    }
} finally {
    $stream.Dispose()
}

# --- SHA-256 ---------------------------------------------------------------
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLower()
Set-Content -LiteralPath "$zipPath.sha256" -Value "$hash  $zipName" -Encoding ascii

$version = '0.0.0'
foreach ($line in Get-Content -LiteralPath (Join-Path $packageDir '__init__.py')) {
    if ($line -match '^\s*__version__\s*=\s*["'']([^"'']+)["'']') { $version = $Matches[1]; break }
}

Write-Host "igz_tb_scenes $version"
Write-Host "  $zipPath"
Write-Host ("  sha256 = ""{0}""" -f $hash)
Write-Host ''
Write-Host '  Paste that sha256 into extensions/igz_tb_scenes.toml and upload'
Write-Host "  $zipName to the GitHub Release of the tag in ``download``."
