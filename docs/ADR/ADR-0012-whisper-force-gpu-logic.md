# ADR-0012: Whisper GPU強制使用ロジックの修正

- **Date**: 2026-06-09
- **Status**: Accepted
- **Deciders**: Gemini

## Context
ユーザーから「設定画面でGPUを使用するかどうか（force_gpu）を選択できるが、本当にGPUを使用するロジックになっているか？」という疑問が提示された。

調査の結果、`src/core/whisper_transcriber.py` の `load_model` 関数において、UIから渡された `force_gpu` フラグを受け取ってはいるものの、実際のデバイス判定ロジックでは `if _is_cuda_available():` のみを評価しており、ユーザーが明示的に「強制する」設定にしていても、内部のCUDA検知関数がFalseを返すと強制的にCPUにフォールバックされるというバグ（ロジックの不備）が存在した。

## Decision
デバイス決定ロジックを以下のように修正し、ユーザーの設定を最優先する仕様に変更した。

```python
if force_gpu or _is_cuda_available():
    device = "cuda"
```

これにより、ユーザーが `force_gpu = True` を設定した場合は、システム側（PyTorchやctranslate2）の初期検知がどうであれ、一旦 `cuda` デバイスでのロードを試行するようになる。ロードに失敗した場合（DLL不足など）は、既存の `try...except` ブロックで捕捉され、安全にCPUへフォールバックされる。

## Consequences
### Positive
- ユーザーの明示的な設定（UIのチェックボックス）が正しくバックエンド（Faster-Whisper）に反映されるようになった。
- CUDAの環境変数の問題などで `_is_cuda_available()` が誤ってFalseを返すような特殊な環境でも、強制的にGPUを使用させることが可能になった。

### Negative / Risks
- GPU（CUDA）が物理的に存在しないPCでこのチェックを入れた場合、内部エラー（ロード失敗）を経てからCPUに切り替わるため、音声ファイルの読み込みや文字起こしの開始に数秒のオーバーヘッドが発生する。

## References
- Issue: ユーザー報告に基づくロジック監査
- PR: N/A
