# ADR-0003: Decoupling PyTorch Dependency and Size Optimization

- **Date**: 2026-05-31
- **Status**: Proposed
- **Deciders**: ayato-labs, Gemini CLI

## Context
現在のプロジェクトは、音声の文字起こしに `faster-whisper` を使用している。`faster-whisper` は内部的に `ctranslate2` を使用しており、推論自体には PyTorch を必要としない。

しかし、現在以下の理由で PyTorch (および `torchaudio`) がプロジェクトに含まれている：
1.  `SoundCardRecorder` における音声のリサンプリング（サンプリングレート変換）処理。
2.  `pyproject.toml` の初期設計における広範な依存関係。

PyTorch を含めることで配布バイナリサイズが 2GB 〜 4GB にまで膨れ上がり、GitHub Release のアセットサイズ制限（2GB）を突破できない、およびユーザーのダウンロード体験を著しく損なうという「技術負債」が発生している。

## Decision
PyTorch 依存を「巨大な負債」と定義し、段階的に切り離すとともに、当面のビルドサイズ問題を解消するための最適化を実施する。
### フェーズ1：ビルド環境の隔離とクリーンアップ（即時実施）
- **環境汚染の防止**: CPU版とGPU版のビルドを完全に独立した仮想環境で行い、CPU版に GPU用DLL（CUDA/cuDNN）が混入するのを防ぐ。
- **不要ライブラリの削除**: コード内で未使用の `torchvision` を依存関係から削除する。
- **開発用ファイルのパージ**: ビルド後の配布物から `.lib`, `.h`, `.cmake` 等の実行に不要なファイルを削除する。
- **自動スモークテストの義務化**: 積極的なファイル削除による「起動不可」リスクを回避するため、CI パイプライン内でビルド直後に EXE を実際に起動し、正常に初期化（DLL の読み込み完了）ができることを検証するステップを必須とする。

## Decision

### フェーズ2：PyTorch からの完全脱却（計画前倒しで完了）
当初は将来の課題としていたが、CI/CDの検証において「フェーズ1のクリーンアップを行っても、`PyInstaller --onefile` で生成される単一バイナリが 2.5GB に達し、GitHub Releaseの 2GB 制限を物理的に突破できない」という事実が判明したため、計画を前倒しして即時実施した。
- **リサンプリングの代替**: 音声キャプチャ時のサンプリングレート変換に使われていた `torchaudio.transforms.Resample` を、軽量な `scipy.signal.resample` に置き換えた。
- **VRAM検出の代替**: `torch.cuda` によるVRAM容量取得ロジックを、システムコマンド（`nvidia-smi`）のサブプロセス呼び出しに置き換えた。
- **依存の完全削除**: `torch`, `torchaudio`, `torchvision` を `pyproject.toml` から完全に削除。これにより、バイナリサイズを数百MB単位にまで劇的に軽量化した。

## Consequences

### Positive
- **配布サイズ制限の突破**: 根本的な容量問題が解決し、GitHub Releaseへの単一 `.exe` ファイルの自動アタッチが安定して成功するようになった。
- **ビルドの安定化**: 巨大なバイナリを含まないため、CI/CD の実行時間が短縮され、ストレージコストも削減される。
- **ランタイムパフォーマンス**: アプリの起動速度が向上し、メモリ使用量が大幅に削減される。

### Negative / Risks
- **リサンプリング精度の検証**: `torchaudio` からの移行時、音声の劣化による文字起こし精度への影響を慎重に検証する必要がある。
- **過渡期のバイナリ管理**: フェーズ2完了までは、依然として PyTorch 由来の DLL 管理が必要。

## References
- Issue: # (Build Size Optimization)
- Related: ADR-0001 (Windows Distribution), ADR-0002 (Speaker Diarization - こちらも将来的に PyTorch 抜きでの実装を検討)
