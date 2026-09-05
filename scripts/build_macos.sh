#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-dev}"
ARCH="$(uname -m)"
python -m PyInstaller --noconfirm --clean packaging/tts_text_mp3.spec
test -d "dist/YomiPalette.app"
mkdir -p release

APP_ARCHIVE="release/YomiPalette_macOS_${ARCH}_${VERSION}.zip"
rm -f "$APP_ARCHIVE" "release/YomiPalette_macOS_${ARCH}_${VERSION}.dmg"
ditto -c -k --sequesterRsrc --keepParent "dist/YomiPalette.app" "$APP_ARCHIVE"

hdiutil create -volname "YomiPalette" -srcfolder "dist/YomiPalette.app" \
  -ov -format UDZO "release/YomiPalette_macOS_${ARCH}_${VERSION}.dmg"
