# システム音声キャプチャの音声データ破損とハルシネーション

**発生日**: 2026-03-23  
**影響範囲**: ライブ文字起こし機能全体  
**ステータス**: 解決済み

---

## 症状

ライブ文字起こし機能でYouTubeや会議音声などのシステム音を録音し、Whisperで文字起こしすると、以下の異常が発生した。

- 実際の発話内容とは無関係な文字列が繰り返し出力される
  - 例: `youtube.com youtube.com youtube.com エンディング ご視聴ありがとうございました`
- 録音されたWAVファイルを再生すると「機械音」のような不自然なノイズになっている
- 音声データの数値（Peak, RMS等）は正常範囲に見えるが、音声として全く意味をなさない

---

## 根本原因

**`soundcard` ライブラリの `numpy.fromstring` 廃止に対するモンキーパッチが、音声バイナリデータを破損させていた。**

### 詳細

1. `soundcard` ライブラリは内部（`mediafoundation.py`）で `numpy.fromstring()` を使用し、Windows Media Foundation のCOMバッファから音声データをPython配列に変換している
2. `numpy` 2.0 以降で `fromstring` のバイナリモードが廃止されたため、`numpy.fromstring = numpy.frombuffer` というモンキーパッチを適用した
3. `fromstring` と `frombuffer` はメモリの読み取り方法（コピー vs ビュー、アライメント）が微妙に異なる
4. その結果、COMバッファのバイト列が**正しいオフセットで解釈されず**、数値としては `float32` の正常範囲内（-1.0 ~ 1.0）に収まるが、**時間軸上では完全に無意味なデータ**が生成された
5. Whisperはこの「意味のないノイズ」を受け取り、学習データ中の頻出フレーズ（`youtube.com`, `ご視聴ありがとうございました`等）をハルシネーションとして出力した

---

## 試行錯誤の記録

### 失敗したアプローチ

| 手法 | 結果 | 失敗の理由 |
|------|------|------------|
| FFmpeg + DirectShow (`dshow`) でシステム音取得 | デバイス選択がマイクになる | Windows環境依存。ステレオミキサーの有効化が必要 |
| `soundcard` + `numpy.fromstring` モンキーパッチ | 機械音（データ破損） | `fromstring` と `frombuffer` のメモリ解釈差異 |
| WAV保存形式の変更（float32, int16, 48kHz, 16kHz） | 全て機械音 | データ自体が破損しているため、出力形式を変えても無意味 |
| サンプルレートの変更（16kHz -> 48kHz） | 機械音変わらず | 破損はサンプルレートではなくバイト解釈の問題 |
| Whisper VADパラメータの厳格化 | 空文字出力 | 入力データが壊れているため、AIが何も検出できなかった |
| `initial_prompt` の削除 | ハルシネーション内容が変化 | 入力データの問題を解決していない |
| `condition_on_previous_text=False` | ループは止まるが幻聴は残る | 入力データの問題を解決していない |
| 音量しきい値の引き上げ | 正常音声まで無視 | Peak値自体は高いため（破損データも高振幅） |

### 成功したアプローチ

**`soundcard` ライブラリを `pyaudiowpatch` に完全置換した。**

`pyaudiowpatch` は PortAudio の Windows フォークで、WASAPI ループバックキャプチャに特化している。`numpy.fromstring` に一切依存せず、`paInt16` 形式の生PCMバイトを直接返すため、データ破損のリスクがない。

---

## 最終的な解決策

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/recorder/soundcard_recorder.py` | `soundcard` -> `pyaudiowpatch` に全面書き換え |
| `pyproject.toml` | 依存関係を `soundcard` -> `PyAudioWPatch` に変更 |
| `src/transcriber.py` | `condition_on_previous_text=False` 追加、`initial_prompt` 削除 |
| `src/live_processor.py` | 音量しきい値の調整（Peak < 0.01 or RMS < 0.001） |

### 技術的なポイント

1. **ネイティブサンプルレートでキャプチャ**: WASAPIループバックは48000Hzで動作。16000Hzを直接要求するとデータが壊れる可能性がある
2. **Python側でリサンプリング**: `torchaudio.transforms.Resample(48000, 16000)` を使用し、Whisperが要求する16kHzに変換
3. **FFmpegへの生バイト転送**: MP3エンコード用のFFmpegパイプには、変換前のネイティブPCMデータをそのまま流す
4. **デバイス検出**: `pyaudiowpatch` の `get_loopback_device_info_generator()` でWASAPIループバックデバイスを自動検出

### 検証コマンド

```bash
# pyaudiowpatch による直接キャプチャテスト
.venv\Scripts\python.exe tests/test_whisper_direct.py
```

検証結果: YouTubeの「このトランプさんの発言は日に日に変わりますし」が正確に文字起こしされた。

---

## 教訓

1. **モンキーパッチは本質的に危険**: APIの互換性が保証されない関数の差し替えは、数値レベルでは正常に見えてもバイナリレベルで破損する「サイレントバグ」を生む
2. **音声データの検証はWAV再生で行うべき**: Peak/RMS等の統計値だけでは破損を検出できない。必ず人間の耳で確認する
3. **ライブラリの廃止に対しては、パッチではなく代替ライブラリへの移行を検討すべき**: 今回は `soundcard` -> `pyaudiowpatch` への移行で即座に解決した
4. **WASAPIループバックはサンプルレート変換を行わない**: マイク入力と異なり、ループバックデバイスはシステムの出力サンプルレート（通常48kHz）をそのまま返す
