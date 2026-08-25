$ErrorActionPreference = "Stop"

if (-not (Get-Command arduino-cli -ErrorAction SilentlyContinue)) {
    throw "arduino-cli is required. Install it and run: arduino-cli core install arduino:avr"
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Fqbn = if ($env:NANO_FQBN) { $env:NANO_FQBN } else { "arduino:avr:nano:cpu=atmega328old" }
$TempRoot = [System.IO.Path]::GetTempPath().TrimEnd('\')
$BuildRoot = Join-Path $TempRoot ("tusi-nano-" + [guid]::NewGuid().ToString("N"))
$SketchRoot = Join-Path $BuildRoot "nano_trigger"

try {
    New-Item -ItemType Directory -Path $SketchRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "firmware\nano\nano_trigger.ino") `
        -Destination (Join-Path $SketchRoot "nano_trigger.ino")
    & arduino-cli compile --fqbn $Fqbn $SketchRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    $ResolvedBuildRoot = [System.IO.Path]::GetFullPath($BuildRoot)
    if (
        $ResolvedBuildRoot.StartsWith($TempRoot + '\', [System.StringComparison]::OrdinalIgnoreCase) -and
        ([System.IO.Path]::GetFileName($ResolvedBuildRoot) -like 'tusi-nano-*')
    ) {
        Remove-Item -LiteralPath $ResolvedBuildRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
