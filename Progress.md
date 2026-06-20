# Progress — AG_language（Antigravity 日本語化パッチ）

## 現在の状態

Antigravity 2.0 Standalone版の日本語化パッチが動作確認済み。翻訳カバレッジの拡大が次のステップ。

## 直近の完了タスク

### 2026-06-20: Standalone版パッチ改善（全6タスク完了）
- argparse導入（`--rollback`, `--dry-run`, `--check`）
- ZIP自動検出（ヒント→フォールバック走査）
- 正規表現エンジン（minified変数名対策）
- 翻訳辞書: リテラル65 + 正規表現2 = 計67パターン
- 安全機能: Translation Match Report、パッチ状態確認
- **in-place パッチ方式**: main.jsのDEFLATEデータのみ差し替え（Goデータ保護）
- コンカテネート型ZIPのconcatオフセット調整

## 次にやること
- 翻訳カバレッジ拡大（設定詳細、ダイアログ本文、ツールチップ等）
- IDE版パッチ（`apply_ja_patch_ide.py`）の同等改善
