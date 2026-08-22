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

このファイルやサービスアカウントJSONをGitへコミットしないでください。

Edge TTSは認証情報なしで利用できます。
