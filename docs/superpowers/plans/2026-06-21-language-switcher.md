# 言語切替機能 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Antigravity 2.0 のWebUIに英語/日本語の即時切替機能を追加する

**Architecture:** main.js 末尾に翻訳ランタイム（IIFE）を注入。MutationObserver でReact再レンダリングを検知し、DOM レベルでテキストを翻訳。言語選択はウィンドウ上部の固定ドロップダウンで行い、設定は localStorage に保持。

**Tech Stack:** JavaScript (vanilla), Python 3.x, zlib

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `i18n_runtime.js` (新規) | 翻訳テーブル + MutationObserver + 言語トグルUI |
| `apply_ja_patch_standalone.py` (変更) | 文字列置換方式 → ランタイム注入方式に変更 |

---

### Task 1: 翻訳ランタイム JavaScript の作成

**Files:**
- Create: `i18n_runtime.js`

- [ ] **Step 1: `i18n_runtime.js` を作成**

以下の内容で新規作成する。IIFE（即時実行関数）形式で、main.js 末尾に追記しても既存コードと干渉しない。

```javascript
;(function(){
"use strict";
var T={
"Always Ask":"常に確認",
"Always Allow":"常に許可",
"App Settings":"アプリ設定",
"System Prompt":"システムプロンプト",
"Cancel All Tasks":"すべてのタスクをキャンセル",
"Cancel Task":"タスクをキャンセル",
"Clear":"クリア",
"Conversation History":"会話履歴",
"Disable Task":"タスクを無効化",
"Enable Task":"タスクを有効化",
"Model":"モデル",
"Open Settings":"設定を開く",
"Project Settings":"プロジェクト設定",
"Skills are instructions that extend what Agent can do.":"スキルはエージェントの機能を拡張する指示（インストラクション）です。",
"Rules":"ルール",
"Skills":"スキル",
"Task Logs":"タスクログ",
"Agent Loading":"エージェント読み込み中...",
"Add Scheduled Task":"スケジュールタスクの追加",
"Background Task":"バックグラウンドタスク",
"Log in to use the agent":"エージェントを使用するにはログインしてください",
"No internet. Agent features may not work.":"インターネット接続がありません。エージェント機能が動作しない可能性があります。",
"Stop Task":"タスクを停止",
"Submit":"送信",
"Workspace Command Access":"コマンド実行権限",
"Workspace File Access":"ファイルアクセス権限",
"Workspace Web Access":"ウェブアクセス権限",
"New Conversation":"新しい会話",
"Delete Conversation":"会話を削除",
"Archive Conversation":"会話をアーカイブ",
"Confirm Undo":"元に戻す確認",
"Confirm Browser Interaction":"ブラウザ操作の確認",
"Confirm Window Reload":"ウィンドウ再読込の確認",
"Something went wrong":"エラーが発生しました",
"Good response":"良い回答",
"Bad response":"悪い回答",
"Provide Feedback":"フィードバックを送る",
"Provide feedback":"フィードバック",
"Send Feedback":"フィードバックを送信",
"Try Again":"再試行",
"Reload Window":"ウィンドウを再読込",
"Select Project":"プロジェクトを選択",
"Add Folder":"フォルダーを追加",
"Close Folder":"フォルダーを閉じる",
"Create Project":"プロジェクトを作成",
"Always Proceed":"常に続行",
"Learn more":"詳しく見る",
"Copied":"コピーしました",
"Loading...":"読み込み中...",
"Installing...":"インストール中...",
"Waiting for user input":"ユーザー入力を待機中",
"Background Tasks":"バックグラウンドタスク",
"Appearance":"外観",
"General":"一般",
"Permissions":"権限",
"Customizations":"カスタマイズ",
"Shortcuts":"ショートカット",
"Account":"アカウント",
"Sign In":"サインイン",
"Not Signed In":"未サインイン",
"Copy Path":"パスをコピー",
"Copy File Path":"ファイルパスをコピー",
"Copy File Name":"ファイル名をコピー",
"Code Search":"コード検索",
"Workspace Settings":"ワークスペース設定",
"Token Usage":"トークン使用量"
};
var L=localStorage.getItem("ag_lang")||"en";
function trNode(n){
if(n.nodeType===3){var s=n.textContent,t=s.trim();if(t&&T[t])n.textContent=s.replace(t,T[t])}
else if(n.nodeType===1){for(var i=0;i<n.childNodes.length;i++)trNode(n.childNodes[i]);
if(n.placeholder&&T[n.placeholder])n.placeholder=T[n.placeholder];
if(n.title&&T[n.title])n.title=T[n.title]}
}
function trAll(){
var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
while(w.nextNode()){var s=w.currentNode.textContent,t=s.trim();
if(t&&T[t])w.currentNode.textContent=s.replace(t,T[t])}
document.querySelectorAll("[placeholder]").forEach(function(e){if(T[e.placeholder])e.placeholder=T[e.placeholder]});
document.querySelectorAll("[title]").forEach(function(e){if(T[e.title])e.title=T[e.title]});
}
new MutationObserver(function(ms){if(L!=="ja")return;
ms.forEach(function(m){m.addedNodes.forEach(function(n){trNode(n)})})
}).observe(document.documentElement,{childList:true,subtree:true});
function init(){
if(L==="ja")setTimeout(trAll,200);
var d=document.createElement("div");
d.id="ag-i18n";
d.style.cssText="position:fixed;top:6px;right:52px;z-index:9999;display:flex;align-items:center;gap:4px";
d.innerHTML='<span style="color:#888;font-size:11px">🌐</span>'
+'<select id="ag-lang-sel" style="background:var(--bg-base,#1e1e2e);color:var(--text-normal,#cdd6f4);border:1px solid var(--border-color,#45475a);border-radius:4px;padding:1px 4px;font-size:11px;cursor:pointer;outline:none">'
+'<option value="en">English</option><option value="ja">日本語</option></select>';
document.body.appendChild(d);
var sel=document.getElementById("ag-lang-sel");
sel.value=L;
sel.onchange=function(){
if(sel.value==="en"){localStorage.setItem("ag_lang","en");location.reload()}
else{L="ja";localStorage.setItem("ag_lang","ja");trAll()}
};
}
if(document.body)init();else document.addEventListener("DOMContentLoaded",init);
})();/*ag_i18n_runtime*/
```

末尾の `/*ag_i18n_runtime*/` はパッチ適用状態の検出用署名。

- [ ] **Step 2: サイズ確認**

Run: `python -c "print(len(open('i18n_runtime.js','r',encoding='utf-8').read()),'bytes')"`
Expected: 約 3500-4500 bytes（6KB以下であること）

- [ ] **Step 3: Commit**

```bash
git add i18n_runtime.js
git commit -m "feat: 翻訳ランタイムJS作成（DOM翻訳 + 言語切替UI）"
```

---

### Task 2: パッチスクリプトの改修（文字列置換 → ランタイム注入）

**Files:**
- Modify: `apply_ja_patch_standalone.py`

- [ ] **Step 1: 不要になった翻訳辞書と関数を削除**

以下を削除する:
- `UI_REGEX_TRANSLATIONS` リスト（行82-91付近）
- `UI_TRANSLATIONS` dict（行93-181付近）
- `apply_translations()` 関数
- `validate_translations()` 関数
- `print_validation_report()` 関数

`WIZARD_TRANSLATIONS` dict は `patch_asar()` で引き続き使用するため残す。

- [ ] **Step 2: `inject_i18n_runtime()` 関数を追加**

`WIZARD_TRANSLATIONS` の後、`parse_args()` の前に追加:

```python
def load_i18n_runtime():
    """i18n_runtime.js を読み込む。"""
    runtime_path = os.path.join(os.path.dirname(__file__), "i18n_runtime.js")
    if not os.path.exists(runtime_path):
        print(f"Error: i18n_runtime.js not found at {runtime_path}")
        sys.exit(1)
    with open(runtime_path, "r", encoding="utf-8") as f:
        return f.read()


def inject_i18n_runtime(js_content):
    """main.js 末尾に翻訳ランタイムを追記する。"""
    runtime = load_i18n_runtime()
    return js_content + "\n" + runtime
```

- [ ] **Step 3: `validate_translations()` と `print_validation_report()` を再実装**

翻訳テーブルのキーが main.js 内に存在するか検証する。テーブルは `i18n_runtime.js` から抽出する。

```python
def extract_translation_keys():
    """i18n_runtime.js から翻訳キー（英語文字列）を抽出する。"""
    runtime = load_i18n_runtime()
    keys = []
    import json
    # T={...} ブロックからキーを抽出（JSONとしてパース可能な形式）
    start = runtime.find("var T={")
    if start == -1:
        return keys
    start = runtime.find("{", start)
    depth = 0
    end = start
    for i in range(start, len(runtime)):
        if runtime[i] == "{":
            depth += 1
        elif runtime[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    try:
        table = json.loads(runtime[start:end])
        keys = list(table.keys())
    except json.JSONDecodeError:
        pass
    return keys


def validate_translations(js_content):
    """翻訳キーが main.js 内に存在するか検証する。"""
    keys = extract_translation_keys()
    results = {"matched": [], "missing": []}
    for key in keys:
        quoted = f'"{key}"'
        if quoted in js_content:
            count = js_content.count(quoted)
            results["matched"].append((key, count))
        else:
            results["missing"].append(key)
    return results


def print_validation_report(results):
    """翻訳キー検証結果を表示する。"""
    total = len(results["matched"]) + len(results["missing"])
    print(f"\n=== Translation Key Report ===")
    print(f"Keys found: {len(results['matched'])}/{total}")

    if results["matched"]:
        print(f"\n  [OK] Found in main.js:")
        for key, count in results["matched"]:
            print(f'    "{key}" (x{count})')

    if results["missing"]:
        print(f"\n  [MISS] Not found:")
        for key in results["missing"]:
            print(f'    "{key}"')
```

- [ ] **Step 4: `_patch_main_js_inplace()` を修正**

翻訳適用部分を `apply_translations` → `inject_i18n_runtime` に変更。

現行コード（圧縮データ生成部分）:
```python
co = zlib.compressobj(9, zlib.DEFLATED, -15)
new_compressed = co.compress(translated_js_bytes) + co.flush()
```

新コード — 関数シグネチャ変更:
```python
def _patch_main_js_inplace(region_data, zip_offset_in_region, zip_size, js_content_bytes):
```

`js_content_bytes` は `inject_i18n_runtime()` 適用済みの main.js バイト列。内部ロジックは変更なし（圧縮→in-place書き込み→ヘッダー更新→CD更新）。

- [ ] **Step 5: `patch_language_server()` を修正**

変更点:
- `apply_translations(js_text)` → `inject_i18n_runtime(js_text)` に変更
- `validate_translations` の呼び出しを新しいシグネチャに合わせる

```python
def patch_language_server(dry_run=False):
    zip_offset, zip_size = find_zip_offset(LS_PATH)
    if zip_offset is None:
        print("Error: embedded ZIP not found in language_server.exe")
        sys.exit(1)

    with open(LS_PATH, "rb") as f:
        f.seek(zip_offset)
        zip_bytes = f.read(zip_size)
    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))
    js_text = in_zip.read("main.js").decode("utf-8")

    results = validate_translations(js_text)
    print_validation_report(results)

    if dry_run:
        # サイズチェックも行う
        injected = inject_i18n_runtime(js_text)
        injected_bytes = injected.encode("utf-8")
        co = zlib.compressobj(9, zlib.DEFLATED, -15)
        test_compressed = co.compress(injected_bytes) + co.flush()
        # 元の圧縮サイズを取得
        for info in in_zip.infolist():
            if info.filename == "main.js":
                orig_comp = info.compress_size
                break
        diff = orig_comp - len(test_compressed)
        print(f"\n  Size: original compressed={orig_comp}, new={len(test_compressed)}, margin={diff} bytes")
        if diff < 0:
            print("  WARNING: New compressed size exceeds original! Patch will fail.")
        else:
            print("  OK: Fits within original size.")
        print(f"\n[DRY RUN] language_server.exe への書き込みをスキップ")
        return

    injected = inject_i18n_runtime(js_text)
    translated_bytes = injected.encode("utf-8")

    print("Renaming running language_server.exe to language_server.exe.tmp...")
    if os.path.exists(LS_TMP):
        try:
            os.remove(LS_TMP)
        except Exception as e:
            print(f"Warning: Could not remove old tmp file: {e}")
    os.rename(LS_PATH, LS_TMP)

    print("Reading base executable from tmp file...")
    with open(LS_TMP, "rb") as f:
        exe_data = f.read()

    print("Injecting i18n runtime into main.js in-place...")
    exe_data = _patch_main_js_inplace(exe_data, zip_offset, zip_size, translated_bytes)

    print("Writing modified data to language_server.exe...")
    with open(LS_PATH, "wb") as f:
        f.write(exe_data)
    print("language_server.exe patched successfully.")
```

- [ ] **Step 6: `check_patch_status()` を修正**

ランタイム署名文字列 `ag_i18n_runtime` の存在で判定する。

```python
def check_patch_status():
    """パッチが適用済みかを確認する。"""
    print("=== Patch Status Check ===")

    asar_has_backup = os.path.exists(ASAR_BAK)
    ls_has_backup = os.path.exists(LS_BAK)
    print(f"app.asar backup:           {'EXISTS' if asar_has_backup else 'NOT FOUND'}")
    print(f"language_server.exe backup: {'EXISTS' if ls_has_backup else 'NOT FOUND'}")

    zip_offset, zip_size = find_zip_offset(LS_PATH)
    if zip_offset is None:
        print("Error: Could not locate embedded ZIP")
        return

    with open(LS_PATH, "rb") as f:
        f.seek(zip_offset)
        zip_bytes = f.read(zip_size)

    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))
    js_text = in_zip.read("main.js").decode("utf-8")

    if "ag_i18n_runtime" in js_text:
        print("Patch status: APPLIED (i18n runtime found)")
    else:
        print("Patch status: NOT APPLIED (i18n runtime not found)")
```

- [ ] **Step 7: `import re` を削除（不要になった場合）**

`UI_REGEX_TRANSLATIONS` 削除後、`re` モジュールがどこでも使われていなければ `import re` を削除する。`import struct` と `import zlib` は `_patch_main_js_inplace` で引き続き使用。

- [ ] **Step 8: 動作確認**

Run: `python apply_ja_patch_standalone.py --dry-run`
Expected:
- Translation Key Report が表示される
- Size チェックが `OK: Fits within original size.` と表示される
- `[DRY RUN]` メッセージで終了

Run: `python apply_ja_patch_standalone.py --check`
Expected: `Patch status: NOT APPLIED`

- [ ] **Step 9: Commit**

```bash
git add apply_ja_patch_standalone.py
git commit -m "feat: 文字列置換方式からi18nランタイム注入方式に移行"
```

---

### Task 3: 統合テストと検証

**Files:**
- No file changes (検証のみ)

- [ ] **Step 1: --dry-run で全検証**

Run: `python apply_ja_patch_standalone.py --dry-run`

確認ポイント:
- 翻訳キーのマッチ状況
- 圧縮サイズが余裕内に収まっている
- エラーなし

- [ ] **Step 2: パッチ適用**

Run: `python apply_ja_patch_standalone.py`

確認ポイント:
- バックアップ作成/既存確認
- app.asar パッチ成功
- language_server.exe パッチ成功
- `Localization completed successfully!`

- [ ] **Step 3: --check で適用状態確認**

Run: `python apply_ja_patch_standalone.py --check`
Expected: `Patch status: APPLIED (i18n runtime found)`

- [ ] **Step 4: アプリ起動・目視確認**

1. Antigravity を起動
2. 画面右上に言語ドロップダウン（🌐 English / 日本語）が表示されるか確認
3. 「日本語」を選択 → UIテキストが日本語に変わるか確認
4. 「English」を選択 → ページリロードされ英語に戻るか確認
5. 日本語を選択して閉じる → 再起動時に日本語が維持されるか確認

- [ ] **Step 5: ロールバックテスト**

Run: `python apply_ja_patch_standalone.py --rollback`
Run: `python apply_ja_patch_standalone.py --check`
Expected: `Patch status: NOT APPLIED`

Antigravity を起動 → 言語ドロップダウンが消えている、全て英語に戻っていることを確認。

- [ ] **Step 6: Commit**

```bash
git add apply_ja_patch_standalone.py i18n_runtime.js
git commit -m "feat: 言語切替機能 完成（EN/JP即時切替対応）"
```
