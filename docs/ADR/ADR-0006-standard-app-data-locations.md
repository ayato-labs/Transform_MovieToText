# ADR-0006: Standardizing Application Data Locations on Windows

- **Date**: 2026-05-31
- **Status**: Proposed
- **Deciders**: ayato-labs, Gemini CLI

## Context
現在、本アプリケーションは実行ファイル（`.exe`）と同じディレクトリ、あるいはアプリケーションのソースルートにある `data/`, `logs/` といったフォルダにデータを保存している。

しかし、Windows OSにおいて、ユーザーデータをアプリケーションのインストールディレクトリや実行ファイル周辺に保存することは、以下の理由から推奨されない。
1.  **書き込み権限の制限**: `C:\Program Files` 等に配置された場合、管理者権限なしではデータを書き込めなくなる。
2.  **OS標準への不適合**: Windowsにはユーザーごとの設定やデータを保存するための標準的な場所（`AppData`）が定義されており、これに従わないアプリは「行儀の悪い（Non-compliant）」アプリと見なされる。
3.  **ユーザープロファイルの不整合**: ローミングユーザープロファイルやOSのバックアップ機能が、アプリ固有のデータを正しく捕捉できなくなる。

## Decision
Windowsの設計ガイドラインに準拠し、すべてのデータを標準的なアプリケーションデータディレクトリへ集約する。

1.  **設定・データベース・ログの保存先 (`%APPDATA%`)**:
    - `C:\Users\<Name>\AppData\Roaming\TransformMovieToText\`
    - 理由: 軽量な設定やDBは、異なるデバイス間での同期（Roaming）を考慮し、Roamingディレクトリに配置する。
2.  **巨大なバイナリデータ（モデル等）の保存先 (`%LOCALAPPDATA%`)**:
    - `C:\Users\<Name>\AppData\Local\TransformMovieToText\models\`
    - 理由: 数百MB〜数GBにおよぶ Whisper モデルなどは、デバイス間同期の負荷を避けるため、Localディレクトリに配置する。
3.  **後方互換性の確保（自動マイグレーション）**:
    - アプリ起動時に古い保存場所（`./data/`）をチェックし、データが存在する場合は自動的に新しい場所へ移動させ、整合性を保つ。

## Consequences
### Positive
- **信頼性の向上**: Windowsの標準的なセキュリティモデルおよび権限管理と整合性が取れ、企業環境での安定動作が保証される。
- **クリーンスペースの維持**: ユーザーの作業ディレクトリを実行時生成ファイルで汚染することがなくなり、洗練されたUXを提供できる。
- **配布の柔軟性**: インストーラー形式（MSI等）への将来的な拡張が容易になる。

### Negative / Risks
- **データの隠蔽**: 開発者にとってデータが直接見えにくくなる（`%APPDATA%` は隠しフォルダ）。これに対応するため、アプリ内に「データフォルダを開く」ボタンなどのデバッグ・メンテナンス用ショートカットを実装する必要がある。

## References
- ADR-0001 (Windows Exclusive)
- Microsoft Design Guidelines: [Windows Application Data Folders](https://learn.microsoft.com/en-us/windows/win32/shell/known-folder-ids)
