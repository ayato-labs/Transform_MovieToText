# トラブルシューティング: sherpa-onnx モデルの Protobuf parsing failed エラー

## 発生日
2026-06-01

## 症状
話者分離（Speaker Diarization）パイプラインの初期化時、`sherpa_onnx.OfflineSpeakerDiarization(config)` を呼び出した際に以下のエラーが発生し、プログラムがクラッシュする。

```python
RuntimeError: Load model from models\pyannote-segmentation-3.0.onnx failed:Protobuf parsing failed.
```

## 原因
**自動ダウンロードされたファイルが、有効な ONNX バイナリファイルではなかったため。**

Pythonの `requests` ライブラリを用いて Hugging Face のリポジトリ（`resolve/main/...`）から直接ダウンロードを試みたが、Hugging Face では巨大なモデルファイルは Git LFS (Large File Storage) で管理されている。
適切なLFS解決（リダイレクト処理や認証）を行わない素の HTTP GET リクエストでは、実際の数十MBのバイナリモデルではなく、**数KBの「LFSポインターファイル（単なるテキストデータ）」がダウンロード**されてしまう。
このテキストデータを ONNX ランタイムがパースしようとしたため、`Protobuf parsing failed` エラーとなった。

## ダメだった解決策（失敗したアプローチ）
1. **古いモデルの削除と再ダウンロードの繰り返し:**
   ファイルが壊れていると考え `del models\*.onnx` で削除して再実行したが、取得ロジックが同じ（Hugging Face の LFS リンクへの単純な GET リクエスト）であったため、何度やってもポインターファイルがダウンロードされ、同じエラーが再発した。
2. **Hugging Face の別エンドポイントの推測:**
   APIエンドポイントや別のURLパスを試行したが、パブリックアクセスの制限（401 Unauthorized）や LFS の仕様により、認証なしでの安定したバイナリの直接取得が困難であった。

## 解決策（最終的な対応）
モデルのダウンロード元を Hugging Face から、**sherpa-onnx 公式の GitHub Releases** に変更した。

GitHub Releases のアセットは LFS ポインターではなく実ファイルとして直接ホストされているため、`requests.get` で確実にバイナリをダウンロードできる。

**具体的な実装変更（ModelManagerの改修）:**
1. **URLの変更**: Hugging Face のリンクから、GitHub Releases の直接ダウンロードリンク（`https://github.com/.../releases/download/...`）に変更した。
2. **アーカイブ展開ロジックの追加**: 
   公式が提供する pyannote-segmentation モデルは `.tar.bz2` で圧縮されて配布されている。そのため、ダウンロード後に Python 標準の `tarfile` モジュールを用いて自動で解凍し、中身の `model.onnx` を正しいパスに配置するロジックを `ModelManager` に追加した。

## 教訓
- **MLモデルの自動ダウンロード:** Hugging Face などのリポジトリからモデルをスクリプトで自動ダウンロードする際は、常に Git LFS の仕様を考慮する必要がある。安易な `requests.get` はポインターファイルを取得してしまう罠になりやすい。
- **エラーメッセージの直訳を疑う:** `Protobuf parsing failed` は「パース処理自体のバグ」ではなく、ほとんどの場合「ファイルがONNX形式ではない（HTMLやテキストである）」ことを示している。このような場合は、まず `os.path.getsize()` 等でダウンロードしたファイルが想定されるサイズ（数十MB）を満たしているか確認するべきである。
