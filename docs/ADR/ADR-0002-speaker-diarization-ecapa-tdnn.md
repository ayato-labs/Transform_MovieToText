# ADR-0002: Speaker Diarization via sherpa-onnx and CAM++

- **Date**: 2026-06-01
- **Status**: Accepted
- **Deciders**: ayato-labs, Gemini CLI

## Context
現在のプロジェクトは Whisper を使用した高精度な文字起こしを実現しているが、会議動画や対談など複数人が関与するコンテンツにおいて、「誰が何を話したか」という話者情報（Speaker Identity）の欠如が、実用上の大きな課題となっている。

議事録作成ツールとしての価値を最大化するためには、文字起こしテキストに話者ラベルを付与する「話者分離（Speaker Diarization）」機能の導入が不可欠である。

当初は ECAPA-TDNN (2026-05-31) を検討していたが、ADR-0003（PyTorch依存の分離）および ADR-0005（統合型スマートEXE）の方針を徹底するため、PyTorch を必要とせず、より軽量で高性能な手法への転換が必要となった。

## Decision
**sherpa-onnx** フレームワークと **CAM++** モデルを組み合わせた話者分離を実装する。

1.  **フレームワーク選定**: `sherpa-onnx` を採用する。これは C++ ベースの推論エンジン（Apache-2.0）であり、PyTorch に依存せず ONNX Runtime のみで動作する。
2.  **モデル選定（埋め込み）**: Alibaba 3D-Speaker プロジェクトの **CAM++** を採用する。
    - **効率性**: ECAPA-TDNN と比較してパラメータ数が約半分。
    - **性能**: VoxCeleb 等のベンチマークで ECAPA-TDNN を凌駕する精度。
    - **配布サイズ**: ONNX 形式で 15-20MB 程度と極めて軽量。
3.  **VAD/セグメンテーション**: `sherpa-onnx` エコシステム内で提供されている `pyannote-segmentation-3.0` の ONNX 版等を使用する。
4.  **ライセンス**: `sherpa-onnx` および `CAM++` モデルはいずれも **Apache-2.0** であり、ADR-0004（GPL回避）の方針に適合する。
5.  **ローカル実行**: すべての処理をローカルで完結させる。

## Consequences

### Positive
- **PyTorch 依存の完全排除**: ADR-0003 と完全に一致し、配布バイナリの肥大化を防ぐことができる。
- **高速な推論**: CAM++ は CPU 推論でも高速であり、低スペック PC でも「スマート EXE（ADR-0005）」として実用的な速度で動作する。
- **極小の設置面積**: VAD と埋め込みモデルを合わせても 50MB 以下に収まり、ECAPA-TDNN 採用時よりも大幅に軽量。

### Negative / Risks
- **モデル管理の必要性**: モデルファイルを `%LOCALAPPDATA%`（ADR-0006）等に適切に配備・管理する仕組みが必要。

## References
- ADR-0003 (Decoupling PyTorch)
- ADR-0004 (License Compliance)
- ADR-0005 (Unified Smart EXE)
- ADR-0006 (Standard App Data Locations)
- 3D-Speaker Project: [CAM++](https://github.com/alibaba-damo-academy/3D-Speaker)
- sherpa-onnx: [Diarization Docs](https://k2-fsa.github.io/sherpa/onnx/speaker-diarization/index.html)
