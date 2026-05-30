# Troubleshooting: GitHub Actions CI Recovery (Ruff / TOML / Encoding)

GitHub Actions において、Windows と Linux (Ubuntu) の環境差異に起因する連鎖的なビルドエラーが発生した際の解決記録です。

## 1. 発生した問題

### 1-1. Ruff フォーマットチェックの失敗 (Windows vs Linux)
- **事象**: ローカル (Windows) で `ruff format` を実行しても、GitHub Actions (Linux) で `Would reformat...` と判定され、CI が停止。
- **原因**: Git の `autocrlf` 設定により、Windows では `CRLF`、Linux では `LF` でファイルが展開されるため。Ruff は改行コードの違いを「未フォーマット」と見なす。

### 1-2. TOML パースエラー (不可視文字の混入)
- **事象**: `pyproject.toml` の編集後、`uv` や `ruff` が `TOML parse error at line 5, column 1` を吐いて動作不能に。
- **原因**: Windows のエディタやシェル経由の上書きにより、ファイルの先頭に **BOM (Byte Order Mark)** などの不可視文字が混入。TOML パーサーがこれを不正な文字と判定。

### 1-3. テスト収集エラー (ModuleNotFoundError)
- **事象**: `pytest` が `No module named 'src.config_manager'` と出力し、テストが開始されない。
- **原因**: `src/` 配下のディレクトリ整理(`core/` 等への移動)後、テストコード内のインポートパスが `from src.xxx` のままで、最新の構造に追随できていなかった。

---

## 2. 恒久的な解決策 (Permanent Fixes)

再発防止のため、以下の 3 段階のガードレールを設定しました。

### 2-1. 改行コードの LF 強制固定
プロジェクト全体で **LF** を正義とし、OS 間の解釈差異を無くしました。

- **`.gitattributes`**:
  ```gitattributes
  * text eol=lf
  ```
- **`.editorconfig`**:
  ```editorconfig
  [*]
  end_of_line = lf
  ```
- **`pyproject.toml`**:
  ```toml
  [tool.ruff.format]
  line-ending = "lf"
  ```

### 2-2. バイナリ・クリーンアップ
`pyproject.toml` の破損を直す際は、OS の干渉を受けない **Python のバイナリ書き込み (`wb`)** を使用して再生成します。
```python
with open("pyproject.toml", "wb") as f:
    f.write(content.encode("utf-8")) # BOMなし
```

### 2-3. インデックスの正規化 (Renormalize)
`.gitattributes` 設定後、以下のコマンドでリポジトリ内の全改行コードを LF に再インデックスしました。
```powershell
git add --renormalize .
git commit -m "chore: enforce LF endings"
```

---

## 3. 今後の運用ルール

1. **インポート順のエラー (`I001`)**: `uv run ruff check --fix .` で自動修正してからプッシュすること。
2. **プッシュ時の競合**: `git pull --rebase` を使用し、ローカルのフォーマット済みコミットを常に履歴の先端に置くこと。
3. **設定変更**: `pyproject.toml` を極度に複雑なシェル命令(`&&` 等)で操作せず、Python スクリプトや直接編集で整合性を保つこと。
