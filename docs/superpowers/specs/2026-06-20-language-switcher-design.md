# Antigravity 2.0 言語切替機能 設計書

## 概要

Antigravity 2.0 Standalone版のWebUIに、英語/日本語の即時切替機能を追加する。グローバルメニューに「Language」項目を注入し、DOM レベルでテキストを翻訳する。

## 現行方式からの変更

**現行**: main.js 内の英語文字列を日本語に直接置換（Python の `str.replace` / `re.sub`）
**新方式**: main.js 末尾に翻訳ランタイムスクリプトを注入し、DOM レベルで動的に翻訳

英語文字列は一切変更しない。`UI_TRANSLATIONS` / `UI_REGEX_TRANSLATIONS` による直接置換は廃止。

## アーキテクチャ

```
main.js (React バンドル - 英語のまま)
  └─ 末尾に追記: 翻訳ランタイム IIFE
       ├─ TRANSLATIONS テーブル（EN → JP）
       ├─ MutationObserver（React 再レンダリング検知→翻訳適用）
       ├─ Language メニュー注入（グローバルメニューバー / フォールバック: フローティングボタン）
       └─ localStorage 永続化（key: 'ag_lang', value: 'en' | 'ja'）
```

## 翻訳ランタイム仕様

### 翻訳テーブル

```javascript
const T = {
  "Always Ask": "常に確認",
  "App Settings": "アプリ設定",
  // ... 全65エントリ（現行 UI_TRANSLATIONS から移植）
};
```

正規表現パターン（`UI_REGEX_TRANSLATIONS`）は不要。DOM テキストには minified 変数名が含まれないため、全てリテラルマッチで対応できる。

### 翻訳の適用タイミング

1. **起動時**: `localStorage.getItem('ag_lang') === 'ja'` なら `document.body` 以下の全テキストノードを走査して翻訳
2. **React 再レンダリング時**: `MutationObserver` が `childList` + `subtree` で新規ノードを検知 → 日本語モードなら即座に翻訳適用
3. **EN→JP 切替時**: 全テキストノードを走査して翻訳適用、`localStorage` に保存
4. **JP→EN 切替時**: `localStorage` を `'en'` に設定し、**ページリロード**（React が英語で再描画される）

JP→EN でリロードする理由: 逆引き翻訳は部分一致・重複問題で不完全になりやすい。リロードなら確実。

### テキストノード走査

- `TreeWalker` で `SHOW_TEXT` フィルタを使用
- テキストノードの `textContent.trim()` が翻訳テーブルのキーに完全一致する場合のみ置換
- 部分一致は行わない（誤翻訳を防ぐ）
- `placeholder` 属性も対象（入力フィールドのヒントテキスト）

### MutationObserver

```javascript
new MutationObserver(mutations => {
  if (currentLang !== 'ja') return;
  for (const m of mutations) {
    for (const node of m.addedNodes) {
      // ELEMENT_NODE: 子孫のテキストノードを走査
      // TEXT_NODE: 直接翻訳チェック
    }
  }
}).observe(document.body, { childList: true, subtree: true });
```

## Language メニュー

### 注入戦略

1. **優先**: グローバルメニューバーの DOM 構造を検出し、「Language」ドロップダウンを挿入
   - メニューバーのセレクタは実装時に DOM 調査で特定
   - `MutationObserver` でメニューバーの出現を待機（React の遅延レンダリング対応）
2. **フォールバック**: メニュー注入に失敗した場合（3秒タイムアウト）、画面右下にフローティングボタンを表示

### メニュー項目

- `English` (デフォルト)
- `日本語`

選択中の言語にはチェックマーク表示。

## パッチスクリプト変更

### apply_ja_patch_standalone.py

- `UI_TRANSLATIONS` dict → 翻訳ランタイム JS に移動（Python 側では使わない）
- `UI_REGEX_TRANSLATIONS` list → 削除（DOM 翻訳では不要）
- `apply_translations()` → 削除
- `validate_translations()` → JS 側のテーブル検証に変更（`--dry-run` 用）
- 新規: `inject_i18n_runtime(js_content)` → main.js 末尾にランタイムスクリプトを追記
- in-place パッチ方式は維持（`_patch_main_js_inplace` で圧縮データ差し替え）

### --dry-run の動作

翻訳テーブルの全キーが main.js 内に存在するか検証（現行と同じロジック、参照先がJS側テーブルに変わるだけ）。

### --check の動作

パッチ済み main.js にランタイムスクリプトの署名文字列（例: `ag_i18n_runtime`）が含まれるかで判定。

### --rollback の動作

変更なし（バックアップから復元）。

## サイズ予算

| 項目 | 見積もり |
|------|---------|
| 翻訳テーブル（65エントリ） | ~3.5KB |
| ランタイム（Observer + TreeWalker） | ~1.5KB |
| メニュー注入 + フォールバック | ~1.0KB |
| 合計（非圧縮追加分） | ~6.0KB |

制約: 圧縮後のサイズが元の圧縮サイズ（2,245,769 bytes）以下であること。
現行パッチ（文字列置換）では 2,237,911 bytes（余裕 7,858 bytes）。
新方式では文字列置換を行わないため、圧縮ペナルティが小さく、余裕は同等以上の見込み。
