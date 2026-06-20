# Antigravity 2.0 日本語化パッチ改善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `apply_ja_patch_standalone.py` を改善し、ZIP自動検出・翻訳辞書拡充・正規表現対応・安全機能を追加する

**Architecture:** 単一ファイル構成を維持。翻訳エンジンを「正規表現（コンテキスト付き）→ リテラル置換」の2段階に分離し、minified変数名の変更に耐性を持たせる。ZIPオフセットは既知値を試行後、フォールバックでバイナリ走査する。

**Tech Stack:** Python 3.x (標準ライブラリのみ: zipfile, io, re, struct, argparse)

---

## Task 1: argparse導入 + コマンドライン引数の整理

**Files:**
- Modify: `apply_ja_patch_standalone.py:1-10` (imports), `apply_ja_patch_standalone.py:240-268` (main)

- [ ] **Step 1: argparse を追加し、既存の `--rollback` と新規フラグを統合**

`main()` 関数の `sys.argv` 手動パースを `argparse` に置き換える。`--dry-run` と `--check` も定義しておく（実装は後続タスク）。

```python
import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description="Antigravity 2.0 Standalone 日本語化パッチ"
    )
    parser.add_argument("--rollback", action="store_true",
                        help="バックアップから元の状態に復元する")
    parser.add_argument("--dry-run", action="store_true",
                        help="実際の変更を行わず、マッチ結果のみ表示する")
    parser.add_argument("--check", action="store_true",
                        help="パッチ適用状態を確認する")
    return parser.parse_args()
```

- [ ] **Step 2: main() を書き換え**

```python
def main():
    args = parse_args()

    if args.rollback:
        rollback()
        return

    if args.check:
        check_patch_status()
        return

    print("=== Antigravity 2.0 Standalone Japanese Patch ===")

    if not args.dry_run:
        terminate_electron_only()
        create_backups()

    temp_dir = os.path.join(os.path.dirname(__file__), "temp_asar")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    try:
        patch_asar(temp_dir, dry_run=args.dry_run)
        patch_language_server(dry_run=args.dry_run)
        if args.dry_run:
            print("\n[DRY RUN] 上記が適用予定の変更です。実際のファイルは変更されていません。")
        else:
            print("\nLocalization completed successfully! You can now restart Antigravity.")
    except Exception as e:
        print(f"\nAn error occurred during patching: {e}")
        if not args.dry_run:
            print("Restoring backups...")
            rollback()
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
```

注: `check_patch_status()` はこの時点ではスタブ（`pass`）でよい。Task 5 で実装する。

```python
def check_patch_status():
    pass
```

- [ ] **Step 3: `import sys` のうち `sys.argv` 直接参照を削除し、`sys.exit` のみ残す**

`main()` 内の `if len(sys.argv) > 1 and sys.argv[1] == "--rollback":` ブロックを削除（argparse に移行済み）。

- [ ] **Step 4: 動作確認**

Run: `python apply_ja_patch_standalone.py --help`
Expected: ヘルプメッセージが表示される（`--rollback`, `--dry-run`, `--check` の説明）

Run: `python apply_ja_patch_standalone.py --dry-run`
Expected: エラーなく実行される（この時点では patch_asar/patch_language_server が dry_run 引数を受け取れないのでエラーになる可能性あり → Step 5 で対応）

- [ ] **Step 5: patch_asar, patch_language_server に dry_run 引数を追加（スタブ）**

両関数のシグネチャに `dry_run=False` を追加。dry_run=True の場合は「書き込み処理をスキップ」する分岐を入れる。具体的な dry_run 出力は Task 5 で実装。

`patch_asar`:
```python
def patch_asar(temp_dir, dry_run=False):
    if dry_run:
        print("[DRY RUN] app.asar のパッチをスキップ（ASAR展開にはnpxが必要なため）")
        return
    # ... existing code unchanged ...
```

`patch_language_server`:
```python
def patch_language_server(dry_run=False):
    # ... ZIP extraction and translation logic ...
    if dry_run:
        print("[DRY RUN] language_server.exe への書き込みをスキップ")
        return
    # ... write logic ...
```

- [ ] **Step 6: Commit**

```bash
git add apply_ja_patch_standalone.py
git commit -m "refactor: argparse導入、--dry-run/--check フラグ追加"
```

---

## Task 2: ZIP自動検出 + バージョン検証

**Files:**
- Modify: `apply_ja_patch_standalone.py:17-19` (constants), `apply_ja_patch_standalone.py:180-238` (patch_language_server)

- [ ] **Step 1: `_validate_and_measure_zip` ヘルパー関数を追加**

定数定義の直後（`ZIP_TARGET_SIZE` の後）に追加。

```python
def _validate_and_measure_zip(data):
    """data が main.js を含む ZIP かを検証し、ZIPサイズを返す。失敗時は None。"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        if "main.js" not in zf.namelist():
            return None
        eocd_sig = b"PK\x05\x06"
        eocd_pos = data.rfind(eocd_sig)
        if eocd_pos == -1:
            return None
        comment_len = int.from_bytes(data[eocd_pos + 20:eocd_pos + 22], "little")
        zip_size = eocd_pos + 22 + comment_len
        return zip_size
    except Exception:
        return None
```

- [ ] **Step 2: `find_zip_offset` 関数を追加**

```python
def find_zip_offset(exe_path, hint_offset=ZIP_START_OFFSET):
    """バイナリ内の埋め込みZIPを自動検出する。既知オフセット→フォールバック走査。"""
    file_size = os.path.getsize(exe_path)

    with open(exe_path, "rb") as f:
        # Phase 1: 既知オフセットを試行
        if hint_offset < file_size:
            f.seek(hint_offset)
            sig = f.read(4)
            if sig == b"PK\x03\x04":
                f.seek(hint_offset)
                data = f.read(min(5_000_000, file_size - hint_offset))
                zip_size = _validate_and_measure_zip(data)
                if zip_size:
                    print(f"ZIP found at known offset: {hint_offset} (size: {zip_size})")
                    return hint_offset, zip_size

        # Phase 2: バイナリ後半を走査（Go binary の後方に埋め込まれている想定）
        print("Known offset mismatch. Scanning binary for embedded ZIP...")
        scan_size = min(30_000_000, file_size)
        scan_start = file_size - scan_size
        f.seek(scan_start)
        buf = f.read(scan_size)

        idx = 0
        while idx < len(buf) - 4:
            idx = buf.find(b"PK\x03\x04", idx)
            if idx == -1:
                break
            candidate = buf[idx:idx + min(5_000_000, len(buf) - idx)]
            zip_size = _validate_and_measure_zip(candidate)
            if zip_size:
                absolute_offset = scan_start + idx
                print(f"ZIP found by scan at offset: {absolute_offset} (size: {zip_size})")
                return absolute_offset, zip_size
            idx += 4

    return None, None
```

- [ ] **Step 3: `patch_language_server` を自動検出ベースに書き換え**

関数冒頭で `find_zip_offset` を呼び、結果を使う。ハードコードの `ZIP_START_OFFSET` / `ZIP_TARGET_SIZE` は定数として残す（ヒントとして使用）。

```python
def patch_language_server(dry_run=False):
    # 1. ZIP自動検出
    source_path = LS_BAK if os.path.exists(LS_BAK) else LS_PATH
    zip_offset, zip_size = find_zip_offset(source_path if not dry_run else LS_PATH)
    if zip_offset is None:
        print("Error: embedded ZIP not found in language_server.exe")
        sys.exit(1)

    if not dry_run:
        # 2. Rename running binary
        print("Renaming running language_server.exe to language_server.exe.tmp...")
        if os.path.exists(LS_TMP):
            try:
                os.remove(LS_TMP)
            except Exception as e:
                print(f"Warning: Could not remove old tmp file: {e}")
        os.rename(LS_PATH, LS_TMP)

    # 3. Read base executable
    read_path = LS_TMP if not dry_run else LS_PATH
    print(f"Reading base executable...")
    with open(read_path, "rb") as f:
        exe_data = bytearray(f.read())

    zip_bytes = exe_data[zip_offset:zip_offset + zip_size]
    if zip_bytes[:4] != b"PK\x03\x04":
        print("Error: Invalid ZIP signature at detected offset.")
        if not dry_run:
            os.rename(LS_TMP, LS_PATH)
        sys.exit(1)

    # 4. Modify web assets
    print("Modifying web assets inside the embedded ZIP...")
    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))
    out_bio = io.BytesIO()
    out_zip = zipfile.ZipFile(out_bio, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)

    for item in in_zip.infolist():
        data = in_zip.read(item.filename)
        if item.filename == 'main.js':
            js_text = data.decode('utf-8')
            js_text = apply_translations(js_text)
            data = js_text.encode('utf-8')
        out_zip.writestr(item, data)

    out_zip.close()
    new_zip_bytes = out_bio.getvalue()

    print(f"New ZIP size (compressed): {len(new_zip_bytes)} bytes")

    new_zip_bytes_padded = pad_zip_to_size(new_zip_bytes, zip_size)
    print(f"Padded ZIP size: {len(new_zip_bytes_padded)} bytes (Target: {zip_size})")

    if dry_run:
        print("[DRY RUN] language_server.exe への書き込みをスキップ")
        return

    # 5. Write back
    exe_data[zip_offset:zip_offset + zip_size] = new_zip_bytes_padded
    print("Writing modified data to language_server.exe...")
    with open(LS_PATH, "wb") as f:
        f.write(exe_data)
    print("language_server.exe patched successfully.")
```

注: `apply_translations()` は次のタスクで実装する。この時点では既存の `for eng, ja in UI_TRANSLATIONS.items(): js_text = js_text.replace(eng, ja)` のままでもよい。

- [ ] **Step 4: 動作確認**

Run: `python apply_ja_patch_standalone.py --dry-run`
Expected: `ZIP found at known offset: 107141712 (size: 2884187)` が表示される

- [ ] **Step 5: Commit**

```bash
git add apply_ja_patch_standalone.py
git commit -m "feat: ZIP自動検出とフォールバック走査を追加"
```

---

## Task 3: 正規表現ベースの翻訳エンジン

**Files:**
- Modify: `apply_ja_patch_standalone.py` (imports に `re` 追加、翻訳辞書の構造変更、`apply_translations` 関数追加)

- [ ] **Step 1: `import re` を追加**

ファイル先頭の import セクションに `import re` を追加。

- [ ] **Step 2: 翻訳辞書を2層構造に分離**

既存の `UI_TRANSLATIONS` dict をそのまま残しつつ、minified変数名に依存するパターンを `UI_REGEX_TRANSLATIONS` リストに移動。

```python
# Phase 1: Context-aware regex patterns (run FIRST)
# minified変数名（a, c, f 等）がバージョン更新で変わっても動作する
UI_REGEX_TRANSLATIONS = [
    # title: <var> ?? "Workspace Settings"
    (r'title:\w+\?\?"Workspace Settings"',
     lambda m: m.group(0).replace('"Workspace Settings"', '"ワークスペース設定"')),
    # hideBreakdownForGroups: <var> = ["System Prompt"]
    (r'hideBreakdownForGroups:\w+=\["System Prompt"\]',
     lambda m: m.group(0).replace('"System Prompt"', '"システムプロンプト"')),
]

# Phase 2: Literal string replacements (run AFTER regex)
UI_TRANSLATIONS = {
    # --- Permission Options ---
    '"Always Ask"': '"常に確認"',
    '"Always Deny"': '"常に拒否"',
    '"Always Allow"': '"常に許可"',
    '"Always Proceed"': '"常に続行"',
    # --- Settings Sections ---
    'title:"Token Usage"': 'title:"トークン使用量"',
    '"App Settings"': '"アプリ設定"',
    '"Project Settings"': '"プロジェクト設定"',
    '"System Prompt"': '"システムプロンプト"',
    # ... (残りは既存辞書をそのまま維持)
}
```

注: `UI_TRANSLATIONS` から以下のエントリを**削除**する（`UI_REGEX_TRANSLATIONS` に移行済み）:
- `'title:c??"Workspace Settings"': 'title:c??"ワークスペース設定"'`
- `'hideBreakdownForGroups:f=["System Prompt"]': 'hideBreakdownForGroups:f=["システムプロンプト"]'`
- `'hideBreakdownForGroups:a=["System Prompt"]': 'hideBreakdownForGroups:a=["システムプロンプト"]'`

- [ ] **Step 3: `apply_translations` 関数を追加**

```python
def apply_translations(content):
    """正規表現パターン → リテラル置換の順で翻訳を適用する。"""
    # Phase 1: Regex (context-aware, handles minified variable names)
    for pattern, replacement in UI_REGEX_TRANSLATIONS:
        content = re.sub(pattern, replacement, content)
    # Phase 2: Literal
    for eng, ja in UI_TRANSLATIONS.items():
        content = content.replace(eng, ja)
    return content
```

- [ ] **Step 4: `patch_language_server` 内の翻訳ループを `apply_translations` 呼び出しに置換**

既存コード:
```python
for eng, ja in UI_TRANSLATIONS.items():
    js_text = js_text.replace(eng, ja)
```

置換後:
```python
js_text = apply_translations(js_text)
```

- [ ] **Step 5: `patch_asar` 内の翻訳ループもリファクタ**

WIZARD_TRANSLATIONS は単純な文字列置換のみなので、既存の `for` ループをそのまま残す（正規表現不要）。変更なし。

- [ ] **Step 6: 動作確認**

Run: `python apply_ja_patch_standalone.py --dry-run`
Expected: エラーなく完了。ZIP読み取り→翻訳適用→書き込みスキップのフロー。

- [ ] **Step 7: Commit**

```bash
git add apply_ja_patch_standalone.py
git commit -m "feat: 正規表現ベースの翻訳エンジンを追加（minified変数名対策）"
```

---

## Task 4: 翻訳辞書の大幅拡充

**Files:**
- Modify: `apply_ja_patch_standalone.py` (`UI_TRANSLATIONS` dict を拡充)

- [ ] **Step 1: 実際のバイナリから翻訳候補を検証**

`--dry-run` で main.js を展開し、以下の候補文字列が実際に存在するか Grep で確認する。存在しないものはスキップ。

確認対象（PowerShell でワンライナー実行）:
```powershell
Add-Type -AssemblyName System.IO.Compression
$path = "C:\Users\ueyam\AppData\Local\Programs\Antigravity\resources\bin\language_server.exe"
$fs = [System.IO.File]::OpenRead($path); $fs.Seek(107141712, [System.IO.SeekOrigin]::Begin) | Out-Null
$buf = New-Object byte[] 2884187; $fs.Read($buf, 0, 2884187) | Out-Null; $fs.Close()
$ms = New-Object System.IO.MemoryStream(,$buf)
$zip = New-Object System.IO.Compression.ZipArchive($ms, [System.IO.Compression.ZipArchiveMode]::Read)
$entry = $zip.GetEntry("main.js"); $stream = $entry.Open()
$reader = New-Object System.IO.StreamReader($stream); $content = $reader.ReadToEnd()
$reader.Close(); $stream.Close(); $zip.Dispose(); $ms.Dispose()
# Search for each candidate string
$candidates = @(
    '"New Conversation"', '"Delete Conversation"', '"Archive Conversation"',
    '"Confirm Undo"', '"Something went wrong"', '"Good response"', '"Bad response"',
    '"Provide Feedback"', '"Send Feedback"', '"Try Again"', '"Reload Window"',
    '"Select Project"', '"Add Folder"', '"Close Folder"', '"Create Project"',
    '"Background Tasks"', '"Code Search"', '"Learn more"',
    '"Appearance"', '"General"', '"Permissions"', '"Customizations"', '"Shortcuts"',
    '"Account"', '"Copied"', '"Loading..."', '"Installing..."',
    '"Copy Path"', '"Copy File Path"', '"Copy File Name"',
    '"Sign In"', '"Not Signed In"', '"Provide feedback"',
    '"Confirm Browser Interaction"', '"Confirm Window Reload"',
    '"Waiting for user input"', '"Remove"'
)
foreach ($c in $candidates) {
    $count = ([regex]::Matches($content, [regex]::Escape($c))).Count
    if ($count -gt 0) { Write-Output "  FOUND ($count): $c" }
    else { Write-Output "  MISSING: $c" }
}
```

MISSING のものは辞書に入れない。FOUND のものだけ追加する。

- [ ] **Step 2: 確認済みの翻訳エントリを `UI_TRANSLATIONS` に追加**

以下は事前調査で存在が確認されているエントリ。Step 1 の結果に基づいて最終リストを確定する。

```python
UI_TRANSLATIONS = {
    # === 既存エントリ（変更なし） ===
    '"Always Ask"': '"常に確認"',
    '"Always Deny"': '"常に拒否"',
    '"Always Allow"': '"常に許可"',
    'title:"Token Usage"': 'title:"トークン使用量"',
    '"App Settings"': '"アプリ設定"',
    '"System Prompt"': '"システムプロンプト"',
    '"Cancel All Tasks"': '"すべてのタスクをキャンセル"',
    '"Cancel Task"': '"タスクをキャンセル"',
    '"Clear"': '"クリア"',
    '"Close Settings"': '"設定を閉じる"',
    '"Conversation History"': '"会話履歴"',
    '"Disable Task"': '"タスクを無効化"',
    '"Enable Task"': '"タスクを有効化"',
    '"Enter a prompt for the agent"': '"エージェントへのプロンプトを入力..."',
    '"Model"': '"モデル"',
    '"Open Settings"': '"設定を開く"',
    '"Project Settings"': '"プロジェクト設定"',
    '"Skills are instructions that extend what Agent can do."': '"スキルはエージェントの機能を拡張する指示（インストラクション）です。"',
    '"Rules"': '"ルール"',
    '"Skills"': '"スキル"',
    '"Task Logs"': '"タスクログ"',
    '"Agent Loading"': '"エージェント読み込み中..."',
    '"Add Scheduled Task"': '"スケジュールタスクの追加"',
    '"Background Task"': '"バックグラウンドタスク"',
    '"Log in to use the agent"': '"エージェントを使用するにはログインしてください"',
    '"No internet. Agent features may not work."': '"インターネット接続がありません。エージェント機能が動作しない可能性があります。"',
    '"Stop Task"': '"タスクを停止"',
    '"Submit"': '"送信"',
    '"Workspace Command Access"': '"コマンド実行権限"',
    '"Workspace File Access"': '"ファイルアクセス権限"',
    '"Workspace Web Access"': '"ウェブアクセス権限"',

    # === 新規エントリ ===
    # --- Conversation Actions ---
    '"New Conversation"': '"新しい会話"',
    '"Delete Conversation"': '"会話を削除"',
    '"Archive Conversation"': '"会話をアーカイブ"',

    # --- Confirmations / Dialogs ---
    '"Confirm Undo"': '"元に戻す確認"',
    '"Confirm Browser Interaction"': '"ブラウザ操作の確認"',
    '"Confirm Window Reload"': '"ウィンドウ再読込の確認"',
    '"Something went wrong"': '"エラーが発生しました"',

    # --- Feedback ---
    '"Good response"': '"良い回答"',
    '"Bad response"': '"悪い回答"',
    '"Provide Feedback"': '"フィードバックを送る"',
    '"Provide feedback"': '"フィードバック"',
    '"Send Feedback"': '"フィードバックを送信"',

    # --- Actions ---
    '"Try Again"': '"再試行"',
    '"Reload Window"': '"ウィンドウを再読込"',
    '"Select Project"': '"プロジェクトを選択"',
    '"Add Folder"': '"フォルダーを追加"',
    '"Close Folder"': '"フォルダーを閉じる"',
    '"Create Project"': '"プロジェクトを作成"',
    '"Always Proceed"': '"常に続行"',
    '"Learn more"': '"詳しく見る"',
    '"Copied"': '"コピーしました"',

    # --- Status ---
    '"Loading..."': '"読み込み中..."',
    '"Installing..."': '"インストール中..."',
    '"Waiting for user input"': '"ユーザー入力を待機中"',
    '"Background Tasks"': '"バックグラウンドタスク"',

    # --- Settings Sections ---
    '"Appearance"': '"外観"',
    '"General"': '"一般"',
    '"Permissions"': '"権限"',
    '"Customizations"': '"カスタマイズ"',
    '"Shortcuts"': '"ショートカット"',
    '"Account"': '"アカウント"',

    # --- Auth ---
    '"Sign In"': '"サインイン"',
    '"Not Signed In"': '"未サインイン"',

    # --- Copy Actions ---
    '"Copy Path"': '"パスをコピー"',
    '"Copy File Path"': '"ファイルパスをコピー"',
    '"Copy File Name"': '"ファイル名をコピー"',

    # --- Code / Search ---
    '"Code Search"': '"コード検索"',
}
```

- [ ] **Step 3: 動作確認**

Run: `python apply_ja_patch_standalone.py --dry-run`
Expected: エラーなく完了

- [ ] **Step 4: Commit**

```bash
git add apply_ja_patch_standalone.py
git commit -m "feat: 翻訳辞書を拡充（+35エントリ追加、計70+）"
```

---

## Task 5: 安全機能の実装（--dry-run 詳細出力, --check, 事前検証）

**Files:**
- Modify: `apply_ja_patch_standalone.py`

- [ ] **Step 1: `validate_translations` 関数を追加**

パッチ適用前に、全翻訳パターンが現在のバイナリに実際にマッチするか検証する関数。

```python
def validate_translations(js_content):
    """全翻訳パターンのマッチ状況を検証し、結果を返す。"""
    results = {"matched": [], "missing": [], "regex_matched": [], "regex_missing": []}

    for eng, ja in UI_TRANSLATIONS.items():
        if eng in js_content:
            count = js_content.count(eng)
            results["matched"].append((eng, ja, count))
        else:
            results["missing"].append((eng, ja))

    for pattern, replacement in UI_REGEX_TRANSLATIONS:
        matches = re.findall(pattern, js_content)
        if matches:
            results["regex_matched"].append((pattern, len(matches)))
        else:
            results["regex_missing"].append((pattern,))

    return results
```

- [ ] **Step 2: `print_validation_report` 関数を追加**

```python
def print_validation_report(results):
    """翻訳マッチ検証結果を表示する。"""
    total_literal = len(results["matched"]) + len(results["missing"])
    total_regex = len(results["regex_matched"]) + len(results["regex_missing"])

    print(f"\n=== Translation Match Report ===")
    print(f"Literal: {len(results['matched'])}/{total_literal} matched")
    print(f"Regex:   {len(results['regex_matched'])}/{total_regex} matched")

    if results["matched"]:
        print(f"\n  [OK] Literal matches:")
        for eng, ja, count in results["matched"]:
            print(f"    {eng} -> {ja} (x{count})")

    if results["regex_matched"]:
        print(f"\n  [OK] Regex matches:")
        for pattern, count in results["regex_matched"]:
            print(f"    /{pattern}/ (x{count})")

    if results["missing"]:
        print(f"\n  [MISS] Not found (will be skipped):")
        for eng, ja in results["missing"]:
            print(f"    {eng}")

    if results["regex_missing"]:
        print(f"\n  [MISS] Regex not matched:")
        for (pattern,) in results["regex_missing"]:
            print(f"    /{pattern}/")
```

- [ ] **Step 3: `--dry-run` の詳細出力を実装**

`patch_language_server` の dry_run 分岐に検証レポートを組み込む。

```python
def patch_language_server(dry_run=False):
    source_path = LS_PATH
    zip_offset, zip_size = find_zip_offset(source_path)
    if zip_offset is None:
        print("Error: embedded ZIP not found in language_server.exe")
        sys.exit(1)

    with open(source_path, "rb") as f:
        f.seek(zip_offset)
        zip_bytes = f.read(zip_size)

    if zip_bytes[:4] != b"PK\x03\x04":
        print("Error: Invalid ZIP signature at detected offset.")
        sys.exit(1)

    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))

    if dry_run:
        # Read main.js and show validation report
        js_data = in_zip.read("main.js").decode("utf-8")
        results = validate_translations(js_data)
        print_validation_report(results)
        print(f"\n[DRY RUN] language_server.exe への書き込みをスキップ")
        return

    # --- Normal patch flow (non-dry-run) ---
    # Rename running binary
    print("Renaming running language_server.exe to language_server.exe.tmp...")
    if os.path.exists(LS_TMP):
        try:
            os.remove(LS_TMP)
        except Exception as e:
            print(f"Warning: Could not remove old tmp file: {e}")
    os.rename(LS_PATH, LS_TMP)

    print("Reading base executable from tmp file...")
    with open(LS_TMP, "rb") as f:
        exe_data = bytearray(f.read())

    zip_bytes = exe_data[zip_offset:zip_offset + zip_size]

    print("Modifying web assets inside the embedded ZIP...")
    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))
    out_bio = io.BytesIO()
    out_zip = zipfile.ZipFile(out_bio, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)

    for item in in_zip.infolist():
        data = in_zip.read(item.filename)
        if item.filename == 'main.js':
            js_text = data.decode('utf-8')
            results = validate_translations(js_text)
            print_validation_report(results)
            js_text = apply_translations(js_text)
            data = js_text.encode('utf-8')
        out_zip.writestr(item, data)

    out_zip.close()
    new_zip_bytes = out_bio.getvalue()

    print(f"New ZIP size (compressed): {len(new_zip_bytes)} bytes")
    new_zip_bytes_padded = pad_zip_to_size(new_zip_bytes, zip_size)
    print(f"Padded ZIP size: {len(new_zip_bytes_padded)} bytes (Target: {zip_size})")

    exe_data[zip_offset:zip_offset + zip_size] = new_zip_bytes_padded
    print("Writing modified data to language_server.exe...")
    with open(LS_PATH, "wb") as f:
        f.write(exe_data)
    print("language_server.exe patched successfully.")
```

- [ ] **Step 4: `check_patch_status` を実装**

```python
def check_patch_status():
    """パッチが適用済みかを確認する。"""
    print("=== Patch Status Check ===")

    # Check backups
    asar_has_backup = os.path.exists(ASAR_BAK)
    ls_has_backup = os.path.exists(LS_BAK)
    print(f"app.asar backup:           {'EXISTS' if asar_has_backup else 'NOT FOUND'}")
    print(f"language_server.exe backup: {'EXISTS' if ls_has_backup else 'NOT FOUND'}")

    # Check if main.js contains Japanese strings
    zip_offset, zip_size = find_zip_offset(LS_PATH)
    if zip_offset is None:
        print("Error: Could not locate embedded ZIP")
        return

    with open(LS_PATH, "rb") as f:
        f.seek(zip_offset)
        zip_bytes = f.read(zip_size)

    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))
    js_text = in_zip.read("main.js").decode("utf-8")

    # Check a sample of Japanese translations
    ja_samples = ['"常に確認"', '"アプリ設定"', '"トークン使用量"', '"エージェント読み込み中..."']
    ja_found = sum(1 for s in ja_samples if s in js_text)

    if ja_found == len(ja_samples):
        print(f"Patch status: APPLIED (Japanese strings found: {ja_found}/{len(ja_samples)})")
    elif ja_found > 0:
        print(f"Patch status: PARTIALLY APPLIED (Japanese strings found: {ja_found}/{len(ja_samples)})")
    else:
        print(f"Patch status: NOT APPLIED (no Japanese strings found)")
```

- [ ] **Step 5: 動作確認**

Run: `python apply_ja_patch_standalone.py --check`
Expected: `Patch status: NOT APPLIED` が表示される（未パッチ状態の場合）

Run: `python apply_ja_patch_standalone.py --dry-run`
Expected: Translation Match Report が表示され、matched/missing の内訳が確認できる

- [ ] **Step 6: Commit**

```bash
git add apply_ja_patch_standalone.py
git commit -m "feat: --dry-run詳細出力、--check、事前検証を実装"
```

---

## Task 6: 統合テストと最終検証

**Files:**
- No file changes (検証のみ)

- [ ] **Step 1: --dry-run で全パターンのマッチ確認**

Run: `python apply_ja_patch_standalone.py --dry-run`

Expected: 
- `ZIP found at known offset: 107141712` 
- Translation Match Report が表示
- MISS が 0 であることを確認（0 でない場合、辞書から該当エントリを削除）

- [ ] **Step 2: パッチ適用**

Run: `python apply_ja_patch_standalone.py`

Expected:
- バックアップ作成
- app.asar パッチ適用
- language_server.exe パッチ適用
- `Localization completed successfully!` 表示

- [ ] **Step 3: --check でパッチ状態確認**

Run: `python apply_ja_patch_standalone.py --check`

Expected: `Patch status: APPLIED`

- [ ] **Step 4: アプリ起動して目視確認**

1. Antigravity を起動
2. トレイアイコン右クリックメニュー確認
3. ブラウザでエージェントUI表示 → 日本語化されているか確認
4. 設定画面を開く → 各セクション名が日本語化されているか確認

- [ ] **Step 5: ロールバックテスト**

Run: `python apply_ja_patch_standalone.py --rollback`

Expected:
- `Restored: ...app.asar` 
- `Restored: ...language_server.exe`
- `Rollback complete.`

Run: `python apply_ja_patch_standalone.py --check`

Expected: `Patch status: NOT APPLIED`

- [ ] **Step 6: 最終 Commit**

問題なければ最終状態をコミット。

```bash
git add apply_ja_patch_standalone.py
git commit -m "feat: Antigravity 2.0 日本語化パッチ v2 完成"
```
