# TTS Text to MP3

TXTおよびEPUBファイルを読み込み、章ごとのMP3を生成するTkinterアプリです。

## 対応プロバイダ

- Edge TTS
- Microsoft Azure Speech
- Google Cloud Text-to-Speech
- OpenAI TTS

## 主な機能

- TXT / EPUBからのテキスト抽出
- EPUBの章ごとのMP3出力
- 言語・ボイスの選択
- ファイル先頭の一文を使ったボイスの音声確認
- 読み上げ速度、音量、ピッチの調整
- 長文の自動分割
- バックグラウンド生成とキャンセル

## セットアップ

Python 3.10以降を使用してください。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 起動

```powershell
python main.py
```

## 認証情報

Azure、Google、OpenAIの認証情報はGUIの「設定...」から入力します。Windowsでは次のファイルに平文で保存されます。

```text
%USERPROFILE%\.tts-text-mp3\config.json
```

このファイルやサービスアカウントJSONをGitへコミットしないでください。macOSでは同じ `~/.tts-text-mp3/config.json`（ホームフォルダ配下）に保存されます。

Edge TTSは認証情報なしで利用できます。

## Windows / macOS向けリリース

PyInstallerで、Windowsは `onedir` 形式、macOSは `.app` を作成します。WindowsではInno SetupによるインストーラーとPortable ZIP、macOSではDMGとZIPを生成できます。SDKの認証情報やユーザー設定はアプリに同梱せず、実行時に各ユーザーのホームフォルダへ保存されます。

アプリ内容に合わせたアイコン（テキスト文書、音声波形、音符）を `assets/app-icon.png` と `assets/app-icon.ico` に収録し、Windowsの実行ファイルへ適用しています。

### ローカルビルド

Windows（PowerShell、Inno Setup 6が必要）:

```powershell
python -m pip install -r requirements.txt pyinstaller
.\scripts\build_windows.ps1 -Version "dev"
```

`release/` に `Setup.exe` とPortable ZIPが出力されます。

macOS（macOS上で実行、PyInstallerのインストールが必要）:

```bash
python -m pip install -r requirements.txt pyinstaller
bash scripts/build_macos.sh dev
```

`release/` に `.app` のZIPとDMGが出力されます。macOSは基本的に実行するMacのアーキテクチャ（IntelまたはApple Silicon）向けにビルドしてください。GitHub Actionsでは両方を別々にビルドします。署名・公証はまだ設定していないため、配布時にmacOSのセキュリティ確認が表示される場合があります。

### GitHub Release

`v` で始まるタグをpushすると、`.github/workflows/release.yml` がWindows、macOS Intel、macOS Apple Siliconをそれぞれビルドし、GitHub Releaseへ自動添付します。

```bash
git tag v1.0.0
git push origin v1.0.0
```

Privateリポジトリでも、Actionsの `GITHUB_TOKEN` に必要な `contents: write` 権限だけを付与して動作します。APIキー、サービスアカウントJSON、`config.json` はリポジトリやReleaseへ含めないでください。
