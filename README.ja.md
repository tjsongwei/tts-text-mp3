[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-CN.md)

# TTS Text to MP3

TXTまたはEPUBファイルを読み込み、文章をMP3音声へ変換するデスクトップアプリです。WindowsとmacOSに対応しています。

Android・iOS向けのモバイル版は、同一リポジトリ内の別プロジェクトとして[`mobile/README.ja.md`](mobile/README.ja.md)で開発しています。モバイル版では認証情報の安全性とSDKの違いにより、一部プロバイダの対応範囲が異なります。

## 主な機能

- TXT / EPUBからのテキスト抽出
- EPUBの章ごとのMP3出力
- 指定文字数ごとのMP3出力
- 言語・ボイスの選択
- 選択した出力単位を使った音声確認
- 読み上げ速度、音量、ピッチの調整
- 長文の自動分割
- バックグラウンド生成とキャンセル
- UIの日本語・英語・簡体中国語切り替え

## 対応プロバイダ

| プロバイダ | 認証情報 |
| --- | --- |
| Edge TTS | 不要 |
| Microsoft Azure Speech | APIキーとリージョンが必要 |
| Google Cloud Text-to-Speech | APIキーまたはサービスアカウントJSONが必要 |
| OpenAI TTS | APIキーが必要 |

## ダウンロード

[最新のGitHub Release](https://github.com/tjsongwei/tts-text-mp3/releases/latest)から、お使いのOSに合ったファイルをダウンロードしてください。

### Windows

| ファイル | 用途 |
| --- | --- |
| `TTS-Text-MP3_Setup_<version>.exe` | 通常のインストール版。スタートメニューへの登録とアンインストールに対応 |
| `TTS-Text-MP3_Windows_Portable_<version>.zip` | インストール不要版。ZIPを展開して `TTS-Text-MP3.exe` を実行 |

通常はSetup版がおすすめです。Portable版を使う場合は、ZIP内から直接起動せず、最初に任意のフォルダへすべて展開してください。

### macOS

Macの種類に合ったDMGまたはZIPを選んでください。

| ファイル名に含まれる表記 | 対象Mac |
| --- | --- |
| `arm64` | Apple Silicon搭載Mac（M1、M2、M3、M4以降） |
| `x86_64` | Intel搭載Mac |

- DMG：開いてアプリを利用する配布形式
- ZIP：展開して `.app` を利用する形式

現在のmacOS版はAppleによるコード署名・公証を行っていません。初回起動時にmacOSの警告が表示された場合は、FinderでアプリをControlキーを押しながらクリックし、「開く」を選択してください。

## 基本的な使い方

1. 使用するTTSプロバイダを選択します。
2. 必要な場合は「設定...」から認証情報を入力します。
3. TXTまたはEPUBファイルを選択します。
4. 出力フォルダ、言語、ボイス、速度などを設定します。
5. 必要に応じて「音声確認」を実行します。
6. 「MP3生成 開始」を押します。

### MP3の分割方法

- 「章ごと」は、EPUBのチャプターごとにMP3を生成します。
- 「文字数ごと」は、TXTまたはEPUBの本文全体を指定文字数以内に分割し、`Part 001`からの連番MP3を生成します。初期値は5000文字です。
- 文字数は読み込み後の本文で数え、空白と改行も1文字とします。指定文字数以内の最後の句点または改行を優先し、区切りがない長文は指定文字数で分割します。
- 選択した分割方法と文字数は、次回起動時に復元されます。

「音声確認」は、出力単位の一覧で選択中の部分から約15秒分のサンプルを生成します。何も選択していない場合は、最初の出力単位を使用します。実際の長さは言語、ボイス、読み上げ速度によって前後します。

Edge TTSは認証情報なしですぐに使用できます。

### 表示言語

画面上部の「表示言語」から日本語、English、簡体中文を切り替えられます。初回起動時はOSの言語を使用し、対応外の言語では英語を表示します。選択した言語は次回起動時にも復元されます。

## 認証情報と設定ファイル

Azure、Google、OpenAIの認証情報はGUIの「設定...」から入力します。設定は次の場所に平文で保存されます。

- Windows：`%USERPROFILE%\.tts-text-mp3\config.json`
- macOS：`~/.tts-text-mp3/config.json`

APIキー、`config.json`、GoogleのサービスアカウントJSONをGitへコミットしたり、他人と共有したりしないでください。これらの認証情報は配布ファイルやGitHub Releaseには含まれていません。

## ソースコードから実行する

Python 3.10以降を使用してください。

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## 配布ファイルをローカルでビルドする

### Windows

PowerShell、PyInstaller、Inno Setup 6が必要です。

```powershell
python -m pip install -r requirements.txt pyinstaller
.\scripts\build_windows.ps1 -Version "dev"
```

`release/` にSetup.exeとPortable ZIPが作成されます。

### macOS

macOS上で実行してください。

```bash
python -m pip install -r requirements.txt pyinstaller
bash scripts/build_macos.sh dev
```

実行したMacのアーキテクチャ向けに、`.app`のZIPとDMGが `release/` に作成されます。

## GitHub Releaseを作成する

`v`で始まるタグをpushすると、GitHub ActionsがWindows Setup版、Windows Portable版、macOS Apple Silicon版、macOS Intel版をビルドしてReleaseへ添付します。

```bash
git tag v0.2.0
git push origin v0.2.0
```

ワークフローは `.github/workflows/release.yml` にあります。認証情報は登録せず、Release作成にはGitHub Actions標準の `GITHUB_TOKEN` と `contents: write` 権限だけを使用します。

## 現在の制限事項

- macOS版は未署名・未公証です。
- Windows版もコード署名していないため、環境によってはSmartScreenの警告が表示される場合があります。
- TTSプロバイダの利用料金、文字数制限、地域制限は各サービスの条件に従います。
- macOS版のアプリアイコンは現在未設定です。

## ライセンス

このプロジェクトは [MIT License](LICENSE) のもとで公開されています。

Copyright (c) 2026 YuluEthan
