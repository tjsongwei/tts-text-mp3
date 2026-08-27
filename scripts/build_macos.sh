#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-dev}"
ARCH="$(uname -m)"
python -m PyInstaller --noconfirm --clean packaging/tts_text_mp3.spec
test -d "dist/TTS-Text-MP3.app"
mkdir -p release

APP_ARCHIVE="release/TTS-Text-MP3_macOS_${ARCH}_${VERSION}.zip"
rm -f "$APP_ARCHIVE" "release/TTS-Text-MP3_macOS_${ARCH}_${VERSION}.dmg"
ditto -c -k --sequesterRsrc --keepParent "dist/TTS-Text-MP3.app" "$APP_ARCHIVE"

hdiutil create -volname "TTS Text to MP3" -srcfolder "dist/TTS-Text-MP3.app" \
  -ov -format UDZO "release/TTS-Text-MP3_macOS_${ARCH}_${VERSION}.dmg"
