# ADR-0011: Local Smart モードと手動プロバイダー設定の同期

- **Date**: 2026-06-09
- **Status**: Accepted
- **Deciders**: Gemini

## Context
本アプリケーションには「Local Smart（ローカル自動最適化）機能」があり、PCスペックに応じてOllamaを自動的に構成する。
しかし、これまではこの機能が「ON」の状態であると、ユーザーが設定画面で手動でプロバイダーを「Gemini API」に変更しても、画面遷移時に再び「Local Smart」が優先され、意図せずOllamaの構成が自動実行されてしまう不整合（競合）が発生していた。

## Decision
設定画面（`SettingsView`）において、ユーザーがAIプロバイダーを手動で変更した場合、**自動的に Local Smart モードを「OFF」に設定する**挙動を採用する。

また、UI初期化時（`initial_load`）に現在のフラグ設定を必ず再読み込みし、UIの状態（プロバイダー設定の反映等）と同期させる。

## Consequences
### Positive
- ユーザーがプロバイダー設定を Gemini に変更すれば、自動的に Ollama の強制構成が停止するようになり、意図したプロバイダー設定が保持される。
- Local Smart モードと手動プロバイダー設定の間に生じていた状態の競合が解消された。
- 不要なエラーログの出力が抑制され、ユーザー体験が向上した。

### Negative / Risks
- 「Local Smart を ON にしたまま、設定画面で Gemini を選び、またメイン画面に戻ってから再度 Local Smart を ON に戻す」という手順が必要になる（自動再開はしない）。

## References
- Issue: #N/A (ユーザー報告に基づき調査・対応)
- PR: N/A
