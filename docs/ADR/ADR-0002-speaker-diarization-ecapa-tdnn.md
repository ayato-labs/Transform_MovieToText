# ADR-0002: Speaker Diarization via ECAPA-TDNN Implementation

- **Date**: 2026-05-31
- **Status**: Proposed
- **Deciders**: ayato-labs, Gemini CLI

## Context
現在のプロジェクトは Whisper を使用した高精度な文字起こしを実現しているが、会議動画や対談など複数人が関与するコンテンツにおいて、「誰が何を話したか」という話者情報（Speaker Identity）の欠如が、実用上の大きな課題となっている。

議事録作成ツールとしての価値を最大化するためには、文字起こしテキストに話者ラベルを付与する「話者分離（Speaker Diarization）」機能の導入が不可欠である。

## Decision
次期主要アップデートの技術選定として、**ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation in TDNN)** をベースとした話者特徴量抽出モデルの採用を検討する。

実装上の具体的方針：
1.  **ライブラリ選定**: SpeechBrain または pyannote-audio をバックエンドとして検討。
2.  **推論エンジン**: Whisper の推論と競合しないよう、必要に応じて VRAM 管理や ONNX 変換による最適化を行う。
3.  **ローカルファースト**: すべての解析プロセスをユーザーのローカル環境で完結させ、生体情報（声紋データ）の外部流出を防止する。

## Consequences

### Positive
- **劇的なUX向上**: 文字起こし結果が「誰の台詞か」を含んだスクリプト形式になり、議事録としての実用性が飛躍的に高まる。
- **SOTA精度の採用**: ECAPA-TDNN は話者照合において現在の最高水準（State-of-the-Art）に近い堅牢性を持ち、ノイズのある動画音声でも高い精度が期待できる。
- **プライバシーの担保**: クラウド型サービスに対する決定的な差別化要因として、機密性の高い会議動画を安全に処理できる。

### Negative / Risks
- **配布サイズと実行負荷**: モデルデータの追加によりバイナリサイズが増大する（数百MB〜1GB程度）。また、Whisper との同時実行時に GPU メモリが不足するリスクがある。
- **依存関係の複雑化**: PyTorch 関連の依存ライブラリが増え、Windows 環境でのパッケージング（PyInstaller/build_exe.py）の難易度が上昇する。
- **計算時間の増加**: 文字起こしプロセスに加えて「話者分離」のステップが追加されるため、総処理時間が増加する。

## References
- Issue: # (TBD)
- Related: ADR-0001 (Windows EXE Distribution)
- Expert Opinion: Speaker Diarization Panel Discussion (2026-05-31)
