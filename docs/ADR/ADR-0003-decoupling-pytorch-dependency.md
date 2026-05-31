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

### フェーズ2：PyTorch からの完全脱却（次期計画）
- **リサンプリングの代替**: `torchaudio.transforms.Resample` を、`numpy`, `scipy.signal`, または軽量な `soxr` 等に置き換える。
- **依存の完全削除**: 置き換え完了後、`torch`, `torchaudio`, `torchvision` を `dependencies` から完全に削除する。これにより、配布サイズを数百MB単位（WhisperモデルとFletランタイムのみ）にまで軽量化する。

## Consequences

### Positive
- **配布サイズの激減**: フェーズ1で 2GB 未満（GitHub制限クリア）、フェーズ2で 500MB 以下を目指せる。
- **ビルドの安定化**: 巨大なバイナリを含まないため、CI/CD の実行時間が短縮され、ストレージコストも削減される。
- **ランタイムパフォーマンス**: アプリの起動速度が向上し、メモリ使用量が大幅に削減される。

### Negative / Risks
- **リサンプリング精度の検証**: `torchaudio` からの移行時、音声の劣化による文字起こし精度への影響を慎重に検証する必要がある。
- **過渡期のバイナリ管理**: フェーズ2完了までは、依然として PyTorch 由来の DLL 管理が必要。

## References
- Issue: # (Build Size Optimization)
- Related: ADR-0001 (Windows Distribution), ADR-0002 (Speaker Diarization - こちらも将来的に PyTorch 抜きでの実装を検討)
