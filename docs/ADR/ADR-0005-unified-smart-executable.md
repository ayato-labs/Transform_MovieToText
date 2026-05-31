# ADR-0005: Unified Smart Executable Distribution

- **Date**: 2026-05-31
- **Status**: Proposed
- **Deciders**: ayato-labs, Gemini CLI

## Context
これまでは、PyTorch とその関連ライブラリ（CUDA DLL等）が数GBにおよぶ巨大なフットプリントを持っていたため、配布サイズを抑える目的で「CPU専用版」と「GPU版」の2種類のバイナリを個別にビルド・配布していた。

しかし、ADR-0003 に基づく PyTorch の完全排除により、GPU駆動に必要な CTranslate2 用の最小限の CUDA ランタイムを含めても、単一の `.exe` ファイルが GitHub Release の 2GB 制限を余裕を持って下回る（数百MB程度）見込みとなった。

## Decision
配布バイナリの分断を廃止し、**「Unified Smart EXE（統合スマート版）」** として単一の実行ファイルに集約する。

1.  **単一バイナリ化**: `TransformMovieToText.exe` という名称の単一ファイルのみを配布する。
2.  **動的ハードウェア検知**: アプリケーション起動時に `ResourceAdvisor` がハードウェアを自動検知し、NVIDIA GPU が利用可能な場合は GPU を、そうでない場合は自動的に CPU を使用する。
3.  **バイナリの包含**: GPU駆動に必要な最小限の DLL (cuBLAS, cuDNN 等) はバイナリに同梱し、ユーザー側での環境構築コストを最小化する。

## Consequences
### Positive
- **ユーザー体験の向上**: ユーザーは自分のPCスペックを気にすることなく、1つのファイルをダウンロードするだけで最適化された実行環境を得られる。
- **配布・管理コストの削減**: CI/CD パイプラインが簡素化され、GitHub Release のアセット管理も単一化される。
- **保守性の向上**: 「CPU版だけで起きるバグ」といった環境依存の切り分けコストが減少し、テストの網羅性が高まる。

### Negative / Risks
- **バイナリサイズの微増**: CPUのみのユーザーにとっては、GPU用DLLが含まれる分、数百MB程度の余計なダウンロードが発生する。しかし、現代のブロードバンド環境および PyTorch 時代の 2.5GB 超過問題に比べれば、許容範囲内であると判断する。

## References
- ADR-0001 (Windows Exclusive)
- ADR-0003 (Decoupling PyTorch)
