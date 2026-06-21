# Progress — AG_language（Antigravity 日本語化パッチ）

## 現在の状態

Antigravity 2.0 Standalone版に言語切替機能（EN/JP即時切替）を実装済み。翻訳エントリ299件、圧縮margin 3.6KB残り。

## 直近の完了タスク

### 2026-06-21: 言語切替機能の実装 + 翻訳辞書拡充
- 方式転換: 文字列直接置換 → DOM翻訳ランタイム注入（`i18n_runtime.js`）
- 言語トグルUI: 左下フローティングドロップダウン（🌐 English / 日本語）
- MutationObserverでReact再レンダリングを検知→即座に翻訳適用
- 翻訳辞書: 66 → 299エントリに段階的拡充（margin 9KB→3.6KB）
- 設定画面全般（権限・外観・モデル・ブラウザ・アプリ・ショートカット等）を翻訳

### 2026-06-20: Standalone版パッチ基盤（全6タスク完了）
- argparse / ZIP自動検出 / in-placeパッチ / コンカテネートZIP対応

## 次にやること
- 翻訳カバレッジの更なる拡大（margin 3.6KB残り）
- `--dry-run` のmargin比較をバックアップ基準に改善
- IDE版パッチ（`apply_ja_patch_ide.py`）の同等改善
