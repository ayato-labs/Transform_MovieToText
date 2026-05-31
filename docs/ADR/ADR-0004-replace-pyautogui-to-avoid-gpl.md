# ADR-0004: Replace PyAutoGUI to Avoid GPLv3 Contamination

- **Date**: 2026-05-31
- **Status**: Accepted
- **Deciders**: ayato-labs, Gemini CLI

## Context
本プロジェクトでは、デスクトップ画面の録画・変化検知（`VisualRecorder`）において、スクリーンショットを取得するために `pyautogui` ライブラリを使用していた。

`pyautogui` 自体は寛容な BSD 3-Clause ライセンスで公開されているが、依存関係の調査（推移的依存関係のチェック）を行った結果、以下のサブモジュールが **GPLv3+（コピーレフト）ライセンス** であることが判明した。
- `MouseInfo` (GPLv3+)
- `PyMsgBox` (GPLv3+)

GPLライセンスを持つコンポーネントを PyInstaller 等で1つのバイナリ（`.exe`）に静的・動的にリンクして配布した場合、GPLの「ウイルス性（コピーレフト条項）」により、**本アプリケーション全体のソースコードもGPLとして公開する法的義務が生じるリスク（ライセンス汚染）**がある。
これは、機密情報を扱う企業やクローズドソースでの商用利用を想定している本プロジェクトの設計思想（ビジネス利用への対応）と致命的に対立する。

## Decision
「商用利用可能なクリーンなライセンス構成」を維持するため、以下の決定を下す。

1.  **`pyautogui` およびその依存関係の完全排除**: `pyproject.toml` から削除し、仮想環境からもアンインストールする。
2.  **`PIL.ImageGrab` への代替**: 画面キャプチャ処理を、すでにプロジェクトで画像処理基盤として導入済みの `Pillow` (PIL) ライブラリが提供する `ImageGrab.grab()` メソッドに置き換える。`Pillow` は MIT-CMU ライセンス（許諾型）であり、商用利用に問題はない。

## Consequences
### Positive
- **法的リスクの排除**: GPL汚染の危険性が完全に排除され、企業法務や情シス部門による導入審査をクリアできる「クリーンなソフトウェア」であることが保証された。
- **依存関係の削減**: 新たなライブラリを追加することなく、既存の `Pillow` を活用したため、パッケージサイズと依存関係の複雑さが低減された。

### Negative / Risks
- **クロスプラットフォーム互換性**: `PIL.ImageGrab` はOSによっては追加の依存（Linuxでのxcb等）を要求する場合があるが、本プロジェクトは ADR-0001 により **Windows特化** を宣言しているため、このリスクは事実上無効化されている（Windows環境ではOSネイティブAPIで問題なく動作する）。

## References
- Issue: # (License compliance audit)
- Related: ADR-0001 (Windows Distribution)
