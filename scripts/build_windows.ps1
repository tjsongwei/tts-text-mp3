param(
    [string]$Version = "dev"
)
$ErrorActionPreference = "Stop"
$env:APP_VERSION = $Version

python -m PyInstaller --noconfirm --clean packaging/tts_text_mp3.spec
if (-not (Test-Path "dist\YomiPalette\YomiPalette.exe")) {
    throw "PyInstaller output was not created."
}

New-Item -ItemType Directory -Force -Path release | Out-Null
$portable = "release\YomiPalette_Windows_Portable_$Version.zip"
if (Test-Path $portable) { Remove-Item -Force $portable }
Compress-Archive -Path "dist\YomiPalette\*" -DestinationPath $portable

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
    $isccPath = $iscc.Source
} else {
    $candidates = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
    )
    $isccPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $isccPath) {
    throw "Inno Setup 6 (ISCC.exe) was not found. Install it with: winget install --id JRSoftware.InnoSetup --exact"
}
& $isccPath packaging/windows-installer.iss
