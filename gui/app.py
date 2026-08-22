"""tkinter メインウィンドウ"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import config
from core.file_reader import Chapter, load_chapters
from core.providers import all_providers, get_provider
from core.providers.base import CancelledError, ProviderError
from core.tts_engine import (
    generate_chapters,
    get_language_codes,
    voices_for_locale,
)


class SettingsDialog(tk.Toplevel):
    def __init__(self, master, provider, on_saved=None):
        super().__init__(master)
        self.provider = provider
        self.on_saved = on_saved
        self.title(f"{provider.label} の設定")
        self.resizable(False, False)
        self.grab_set()

        fields = {**provider.requires_credentials(), **provider.optional_credentials()}
        saved = config.get_provider_credentials(provider.name)

        self.vars: dict[str, tk.StringVar] = {}
        frm = ttk.Frame(self)
        frm.pack(fill="both", expand=True, padx=12, pady=10)
        for index, (field, desc) in enumerate(fields.items()):
            label_row = index * 2
            entry_row = label_row + 1
            ttk.Label(frm, text=desc).grid(
                row=label_row, column=0, columnspan=2, sticky="w", pady=(3, 1)
            )
            var = tk.StringVar(value=saved.get(field, ""))
            self.vars[field] = var
            entry = ttk.Entry(frm, textvariable=var, width=48)
            if field == "api_key":
                entry.config(show="*")
            entry.grid(row=entry_row, column=0, sticky="we", pady=(0, 8))
            if "path" in field or "json" in field or "file" in field:
                ttk.Button(
                    frm,
                    text="参照...",
                    command=lambda v=var: self._browse(v),
                ).grid(row=entry_row, column=1, padx=(4, 0), pady=(0, 8))
        frm.columnconfigure(0, weight=1)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=12, pady=(0, 10))
        ttk.Label(
            btns,
            text="※ APIキーは平文でconfig.jsonに保存されます",
            foreground="#888",
        ).pack(side="left")
        ttk.Button(btns, text="保存", command=self._save).pack(side="right", padx=4)
        ttk.Button(btns, text="キャンセル", command=self.destroy).pack(side="right")

    def _browse(self, var: tk.StringVar) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("全ファイル", "*.*")])
        if path:
            var.set(path)

    def _save(self) -> None:
        values = {k: v.get().strip() for k, v in self.vars.items()}
        required = self.provider.requires_credentials()
        missing = [f for f in required if not values.get(f)]
        if missing:
            messagebox.showwarning("確認", "必須項目を入力してください", parent=self)
            return
        config.set_provider_credentials(self.provider.name, values)
        if self.on_saved is not None:
            self.on_saved()
        self.destroy()


class TTSApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("TTS Text → MP3")
        self.root.geometry("780x680")

        self.chapters: list[Chapter] = []
        self.voices: list[dict] = []
        self.voice_cache: dict[str, list[dict]] = {}
        self.voice_request_id = 0
        self.cancel_event = threading.Event()

        self._build_widgets()

        last = config.get_last("last_provider") or "edge"
        names = [n for n, _label in all_providers()]
        if last in names:
            self.var_provider.set(self._name_to_label[last])
        else:
            self.var_provider.set(self._name_to_label["edge"])
        self.root.after(100, lambda: self._on_provider_changed(initial=True))

    def _build_widgets(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frm_prov = ttk.LabelFrame(self.root, text="プロバイダ")
        frm_prov.pack(fill="x", **pad)
        self.var_provider = tk.StringVar()
        providers = all_providers()
        name_to_label = dict(providers)
        self._name_to_label = name_to_label
        self.cmb_provider = ttk.Combobox(
            frm_prov,
            state="readonly",
            width=24,
            values=[label for _n, label in providers],
            textvariable=self.var_provider,
        )
        self.cmb_provider.pack(side="left", padx=6, pady=6)
        self.cmb_provider.bind("<<ComboboxSelected>>", lambda _e: self._on_provider_changed())
        ttk.Button(frm_prov, text="設定...", command=self.on_open_settings).pack(
            side="left", padx=6, pady=6
        )

        frm_file = ttk.LabelFrame(self.root, text="入力ファイル")
        frm_file.pack(fill="x", **pad)
        self.var_filepath = tk.StringVar()
        ttk.Entry(frm_file, textvariable=self.var_filepath, state="readonly").pack(
            side="left", fill="x", expand=True, padx=6, pady=6
        )
        ttk.Button(frm_file, text="参照...", command=self.on_browse_file).pack(
            side="left", padx=(0, 6), pady=6
        )

        frm_out = ttk.LabelFrame(self.root, text="出力フォルダ")
        frm_out.pack(fill="x", **pad)
        default_out = config.get_last("last_output_dir") or os.path.join(
            os.path.expanduser("~"), "Documents", "tts-mp3"
        )
        self.var_outdir = tk.StringVar(value=default_out)
        ttk.Entry(frm_out, textvariable=self.var_outdir).pack(
            side="left", fill="x", expand=True, padx=6, pady=6
        )
        ttk.Button(frm_out, text="参照...", command=self.on_browse_outdir).pack(
            side="left", padx=(0, 6), pady=6
        )

        frm_voice = ttk.LabelFrame(self.root, text="音声設定")
        frm_voice.pack(fill="x", **pad)

        ttk.Label(frm_voice, text="言語:").grid(row=0, column=0, padx=6, pady=6, sticky="e")
        self.cmb_lang = ttk.Combobox(frm_voice, state="readonly", width=14)
        self.cmb_lang.grid(row=0, column=1, padx=(0, 12), pady=6, sticky="w")
        self.cmb_lang.bind("<<ComboboxSelected>>", lambda _e: self._update_voice_list())

        ttk.Label(frm_voice, text="ボイス:").grid(row=0, column=2, padx=6, pady=6, sticky="e")
        self.cmb_voice = ttk.Combobox(frm_voice, state="readonly", width=32)
        self.cmb_voice.grid(row=0, column=3, padx=(0, 12), pady=6, sticky="w")

        self.var_rate = tk.DoubleVar(value=0)
        self.var_volume = tk.DoubleVar(value=0)
        self.var_pitch = tk.DoubleVar(value=0)
        for row, (label, var, lo, hi, suffix) in enumerate(
            [
                ("速度 (%)", self.var_rate, -50, 50, "%"),
                ("音量 (%)", self.var_volume, -50, 50, "%"),
                ("ピッチ (Hz)", self.var_pitch, -50, 50, "Hz"),
            ],
            start=1,
        ):
            ttk.Label(frm_voice, text=label).grid(row=row, column=0, columnspan=2, padx=6, sticky="w")
            scale = ttk.Scale(frm_voice, from_=lo, to=hi, variable=var, orient="horizontal")
            scale.grid(row=row, column=2, columnspan=2, sticky="we", padx=6, pady=2)
            lbl_val = ttk.Label(frm_voice, width=8)
            lbl_val.grid(row=row, column=4, padx=6, sticky="w")
            var.trace_add(
                "write",
                lambda *_a, v=var, l=lbl_val, s=suffix: l.config(text=f"{int(v.get()):+d}{s}"),
            )
        frm_voice.columnconfigure(3, weight=1)

        frm_ch = ttk.LabelFrame(self.root, text="チャプター")
        frm_ch.pack(fill="both", expand=True, **pad)
        self.tree = ttk.Treeview(frm_ch, columns=("no", "title", "chars"), show="headings", height=7)
        self.tree.heading("no", text="#")
        self.tree.heading("title", text="タイトル")
        self.tree.heading("chars", text="文字数")
        self.tree.column("no", width=40, anchor="center")
        self.tree.column("title", width=480)
        self.tree.column("chars", width=70, anchor="e")
        sb = ttk.Scrollbar(frm_ch, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        sb.pack(side="right", fill="y", pady=6, padx=(0, 6))

        frm_run = ttk.Frame(self.root)
        frm_run.pack(fill="x", **pad)
        self.btn_generate = ttk.Button(frm_run, text="MP3生成 開始", command=self.on_generate)
        self.btn_generate.pack(side="left", padx=6)
        self.btn_cancel = ttk.Button(frm_run, text="キャンセル", command=self.on_cancel, state="disabled")
        self.btn_cancel.pack(side="left", padx=6)

        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", **pad)
        self.var_status = tk.StringVar(value="準備完了")
        ttk.Label(self.root, textvariable=self.var_status, anchor="w").pack(fill="x", padx=10)

    def _current_provider_name(self) -> str:
        label = self.var_provider.get()
        for name, lbl in self._name_to_label.items():
            if lbl == label:
                return name
        return "edge"

    def _current_provider(self):
        return get_provider(self._current_provider_name())

    def _credentials_ready(self, provider) -> bool:
        saved = config.get_provider_credentials(provider.name)
        return all(saved.get(f, "").strip() for f in provider.requires_credentials())

    def _on_provider_changed(self, initial: bool = False) -> None:
        provider = self._current_provider()
        config.set_last("last_provider", provider.name)
        self.voices = []
        self.cmb_voice["values"] = []
        self.cmb_lang["values"] = []

        def open_settings_then_load() -> None:
            SettingsDialog(
                self.root,
                provider,
                on_saved=lambda: self._reload_provider_voices(provider),
            )

        if not self._credentials_ready(provider):
            if initial:
                self.root.after(200, open_settings_then_load)
            else:
                open_settings_then_load()
            self.var_status.set(f"{provider.label}: 認証情報を設定してください")
            return
        self._load_voices_async(provider)

    def on_open_settings(self) -> None:
        provider = self._current_provider()
        SettingsDialog(
            self.root,
            provider,
            on_saved=lambda: self._reload_provider_voices(provider),
        )

    def _reload_provider_voices(self, provider) -> None:
        self.voice_cache.pop(provider.name, None)
        self._load_voices_async(provider)

    def _load_voices_async(self, provider) -> None:
        self.voice_request_id += 1
        request_id = self.voice_request_id
        cached = self.voice_cache.get(provider.name)
        if cached is not None:
            self._voices_loaded(cached, provider, request_id)
            return

        def worker() -> None:
            try:
                provider.validate_credentials()
                voices = provider.list_voices()
            except Exception as e:
                self.root.after(
                    0,
                    lambda err=e, p=provider, rid=request_id: self._voices_failed(
                        err, p, rid
                    ),
                )
                return
            self.root.after(
                0,
                lambda vs=voices, p=provider, rid=request_id: self._voices_loaded(
                    vs, p, rid
                ),
            )

        self.var_status.set("ボイス一覧を取得中...")
        threading.Thread(target=worker, daemon=True).start()

    def _voices_failed(self, err: Exception, provider, request_id: int) -> None:
        if request_id != self.voice_request_id:
            return
        if self._current_provider_name() != provider.name:
            return
        self.var_status.set(f"{provider.label}: ボイス一覧の取得に失敗 ({err})")

    def _voices_loaded(self, voices: list[dict], provider, request_id: int) -> None:
        if request_id != self.voice_request_id:
            return
        if self._current_provider_name() != provider.name:
            return
        self.voice_cache[provider.name] = voices
        self.voices = voices
        codes = ["all"] + get_language_codes(voices)
        self.cmb_lang["values"] = codes
        default = "ja-JP" if "ja-JP" in codes else ("en-US" if "en-US" in codes else "all")
        self.cmb_lang.set(default)
        self._update_voice_list()
        self.var_status.set(f"{provider.label}: 準備完了（ボイス {len(voices)} 種）")

    def _update_voice_list(self) -> None:
        filtered = voices_for_locale(self.voices, self.cmb_lang.get())
        display = [f"{v['ShortName']}  ({v.get('Gender', '')})" for v in filtered]
        self.cmb_voice["values"] = display
        if display:
            self.cmb_voice.current(0)

    def on_browse_file(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("対応ファイル", "*.txt *.epub"),
                ("テキスト", "*.txt"),
                ("EPUB", "*.epub"),
            ]
        )
        if not path:
            return
        try:
            chapters = load_chapters(path)
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return
        self.chapters = chapters
        self.var_filepath.set(path)
        self.tree.delete(*self.tree.get_children())
        for ch in chapters:
            self.tree.insert("", "end", values=(ch.index, ch.title, len(ch.text)))
        total_chars = sum(len(c.text) for c in chapters)
        self.var_status.set(f"{len(chapters)} チャプター / 合計 {total_chars:,} 文字")

    def on_browse_outdir(self) -> None:
        d = filedialog.askdirectory()
        if d:
            self.var_outdir.set(d)

    def on_generate(self) -> None:
        if not self.chapters:
            messagebox.showwarning("確認", "入力ファイルを選択してください")
            return
        if not self.cmb_voice.get():
            messagebox.showwarning("確認", "ボイスを選択してください")
            return
        voice = self.cmb_voice.get().split()[0]
        out_dir = self.var_outdir.get().strip() or "."
        try:
            provider = self._current_provider()
            provider.validate_credentials()
        except ProviderError as e:
            self.on_open_settings()
            messagebox.showwarning("確認", str(e))
            return

        config.set_last("last_output_dir", out_dir)
        self.cancel_event.clear()
        self.btn_generate.config(state="disabled")
        self.btn_cancel.config(state="normal")
        self.progress.start(50)

        def chapter_cb(i: int, total: int, title: str) -> None:
            def ui() -> None:
                self.var_status.set(f"生成中 ({i}/{total}): {title}")

            self.root.after(0, ui)

        def done(outputs: list[str]) -> None:
            def ui() -> None:
                self._finish()
                self.var_status.set(f"完了: {len(outputs)} ファイルを出力しました")
                messagebox.showinfo("完了", f"{len(outputs)} 個のMP3を生成しました\n{out_dir}")

            self.root.after(0, ui)

        def failed(err: BaseException) -> None:
            def ui() -> None:
                self._finish()
                if isinstance(err, CancelledError):
                    self.var_status.set("キャンセルされました")
                else:
                    self.var_status.set(f"エラー: {err}")
                    messagebox.showerror("エラー", str(err))

            self.root.after(0, ui)

        def run() -> None:
            try:
                outputs = generate_chapters(
                    provider,
                    self.chapters,
                    voice,
                    out_dir,
                    rate=f"{int(self.var_rate.get()):+d}%",
                    volume=f"{int(self.var_volume.get()):+d}%",
                    pitch=f"{int(self.var_pitch.get()):+d}Hz",
                    chapter_cb=chapter_cb,
                    cancel_event=self.cancel_event,
                )
                done(outputs)
            except BaseException as e:
                failed(e)

        threading.Thread(target=run, daemon=True).start()

    def _finish(self) -> None:
        self.progress.stop()
        self.btn_generate.config(state="normal")
        self.btn_cancel.config(state="disabled")

    def on_cancel(self) -> None:
        self.cancel_event.set()
        self.var_status.set("キャンセル待ち...")


def run_app() -> None:
    root = tk.Tk()
    TTSApp(root)
    root.mainloop()
