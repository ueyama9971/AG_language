import argparse
import os
import re
import sys
import subprocess
import zipfile
import io
import shutil
import time

# Target Paths
INSTALL_DIR = r"C:\Users\ueyam\AppData\Local\Programs\Antigravity"
ASAR_PATH = os.path.join(INSTALL_DIR, "resources", "app.asar")
ASAR_BAK = ASAR_PATH + ".bak"
LS_PATH = os.path.join(INSTALL_DIR, "resources", "bin", "language_server.exe")
LS_BAK = LS_PATH + ".bak"
LS_TMP = LS_PATH + ".tmp"

# Zip offset and length inside language_server.exe
ZIP_START_OFFSET = 105673492
ZIP_TARGET_SIZE = 4352407


def _validate_and_measure_zip(data):
    """data が main.js を含む ZIP かを検証し、ZIPサイズを返す。失敗時は None。"""
    try:
        eocd_sig = b"PK\x05\x06"
        eocd_pos = data.rfind(eocd_sig)
        if eocd_pos == -1:
            return None
        comment_len = int.from_bytes(data[eocd_pos + 20:eocd_pos + 22], "little")
        zip_size = eocd_pos + 22 + comment_len
        # ZIPサイズ分だけ切り出して検証（末尾にゴミがあるとzipfileが失敗するため）
        zf = zipfile.ZipFile(io.BytesIO(data[:zip_size]))
        if "main.js" not in zf.namelist():
            return None
        return zip_size
    except Exception:
        return None


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

        # Phase 2: バイナリ後半を走査
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


# Phase 1: Context-aware regex patterns (run FIRST)
# minified変数名（c, f, a 等）がバージョン更新で変わっても動作する
UI_REGEX_TRANSLATIONS = [
    # title: <var> ?? "Workspace Settings"
    (r'title:\w+\?\?"Workspace Settings"',
     lambda m: m.group(0).replace('"Workspace Settings"', '"ワークスペース設定"')),
    # hideBreakdownForGroups: <var> = ["System Prompt"]
    (r'hideBreakdownForGroups:\w+=\["System Prompt"\]',
     lambda m: m.group(0).replace('"System Prompt"', '"システムプロンプト"')),
]

# Translation mappings for the Agent Web UI (main.js)
UI_TRANSLATIONS = {
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

# Translation mappings for the Electron Shell Wizard (wizardHtml.js)
WIZARD_TRANSLATIONS = {
    "Welcome to the new Antigravity!": "新しい Antigravity へようこそ！",
    "Antigravity has been redesigned to put agents first with new capabilities. If you'd still like a code editor, you can download it as a separate app named <b>Antigravity IDE</b>.": "Antigravityはエージェントを第一に考えるように再設計されました。もしエディタ版を引き続き使用したい場合は、個別アプリ「Antigravity IDE」をダウンロードできます。",
    "Download the Antigravity IDE": "Antigravity IDE をダウンロードする",
    "Explore the new Antigravity": "新しい Antigravity を使ってみる"
}

def apply_translations(content):
    """正規表現パターン → リテラル置換の順で翻訳を適用する。"""
    # Phase 1: Regex (context-aware, handles minified variable names)
    for pattern, replacement in UI_REGEX_TRANSLATIONS:
        content = re.sub(pattern, replacement, content)
    # Phase 2: Literal
    for eng, ja in UI_TRANSLATIONS.items():
        content = content.replace(eng, ja)
    return content

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


def check_patch_status():
    pass


def terminate_electron_only():
    print("Terminating running Antigravity Electron process (standalone app only)...")
    try:
        # Stop Antigravity standalone app processes by matching their path and excluding IDE
        ps_cmd_app = (
            'Get-Process -Name Antigravity -ErrorAction SilentlyContinue | '
            'Where-Object {$_.Path -like "*Programs\\Antigravity\\Antigravity.exe*" -and $_.Path -notlike "*Antigravity IDE*"} | '
            'Stop-Process -Force'
        )
        subprocess.run(["powershell", "-Command", ps_cmd_app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Antigravity.exe terminated (app.asar is now unlocked).")
        time.sleep(1) # Allow locks to release
    except Exception as e:
        print(f"Warning: Could not terminate processes: {e}")

def create_backups():
    print("Checking and creating backups...")
    if not os.path.exists(ASAR_PATH):
        print(f"Error: app.asar not found at {ASAR_PATH}")
        sys.exit(1)
    if not os.path.exists(LS_PATH):
        print(f"Error: language_server.exe not found at {LS_PATH}")
        sys.exit(1)
        
    if not os.path.exists(ASAR_BAK):
        shutil.copy2(ASAR_PATH, ASAR_BAK)
        print(f"Created backup: {ASAR_BAK}")
    else:
        print(f"Backup already exists: {ASAR_BAK}")
        
    if not os.path.exists(LS_BAK):
        shutil.copy2(LS_PATH, LS_BAK)
        print(f"Created backup: {LS_BAK}")
    else:
        print(f"Backup already exists: {LS_BAK}")

def rollback():
    print("Rolling back to original backups...")
    terminate_electron_only()
    
    # To restore language_server.exe, we also rename the running one first
    if os.path.exists(LS_PATH):
        try:
            if os.path.exists(LS_TMP):
                os.remove(LS_TMP)
            os.rename(LS_PATH, LS_TMP)
        except Exception as e:
            print(f"Warning during rollback rename: {e}")
            
    if os.path.exists(ASAR_BAK):
        shutil.copy2(ASAR_BAK, ASAR_PATH)
        print(f"Restored: {ASAR_PATH}")
    else:
        print(f"Backup not found: {ASAR_BAK}")
        
    if os.path.exists(LS_BAK):
        shutil.copy2(LS_BAK, LS_PATH)
        print(f"Restored: {LS_PATH}")
    else:
        print(f"Backup not found: {LS_BAK}")
    print("Rollback complete.")

def pad_zip_to_size(zip_bytes, target_size):
    eocd_sig = b"PK\x05\x06"
    idx = zip_bytes.rfind(eocd_sig)
    if idx == -1:
        raise ValueError("Invalid zip bytes: no EOCD signature found")
    
    current_size = len(zip_bytes)
    if current_size > target_size:
        raise ValueError(f"Zip too large: current size {current_size} > target size {target_size}. Try compressing more.")
    
    diff = target_size - current_size
    if diff == 0:
        return zip_bytes
        
    comment_len_offset = idx + 20
    current_comment_len = int.from_bytes(zip_bytes[comment_len_offset:comment_len_offset+2], "little")
    
    new_comment_len = current_comment_len + diff
    if new_comment_len > 65535:
        raise ValueError(f"Padding difference {diff} too large for zip comment field")
        
    new_zip_bytes = bytearray(zip_bytes)
    new_zip_bytes[comment_len_offset:comment_len_offset+2] = new_comment_len.to_bytes(2, "little")
    new_zip_bytes.extend(b"\x00" * diff)
    
    return bytes(new_zip_bytes)

def patch_asar(temp_dir, dry_run=False):
    if dry_run:
        print("[DRY RUN] patch_asar: スキップ（実際のファイル変更は行いません）")
        return
    print("Extracting app.asar...")
    subprocess.run(["npx", "asar", "extract", ASAR_PATH, temp_dir], check=True, shell=True)
    
    wizard_file = os.path.join(temp_dir, "dist", "ideInstall", "wizardHtml.js")
    if os.path.exists(wizard_file):
        print(f"Patching {wizard_file}...")
        with open(wizard_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        for eng, ja in WIZARD_TRANSLATIONS.items():
            content = content.replace(eng, ja)
            
        with open(wizard_file, "w", encoding="utf-8") as f:
            f.write(content)
            
        print("Wizard HTML patched.")
    else:
        print("Warning: wizardHtml.js not found in ASAR.")
        
    print("Repackaging app.asar...")
    subprocess.run(["npx", "asar", "pack", temp_dir, ASAR_PATH], check=True, shell=True)
    print("app.asar patched successfully.")

def patch_language_server(dry_run=False):
    # 1. ZIP自動検出 (before any file modifications)
    zip_offset, zip_size = find_zip_offset(LS_PATH)
    if zip_offset is None:
        print("Error: embedded ZIP not found in language_server.exe")
        sys.exit(1)

    if dry_run:
        print(f"[DRY RUN] language_server.exe への書き込みをスキップ")
        return

    # 2. Rename running binary
    print("Renaming running language_server.exe to language_server.exe.tmp...")
    if os.path.exists(LS_TMP):
        try:
            os.remove(LS_TMP)
        except Exception as e:
            print(f"Warning: Could not remove old tmp file: {e}")
    os.rename(LS_PATH, LS_TMP)

    # 3. Read base executable from tmp
    print("Reading base executable from tmp file...")
    with open(LS_TMP, "rb") as f:
        exe_data = bytearray(f.read())

    zip_bytes = exe_data[zip_offset:zip_offset + zip_size]
    if zip_bytes[:4] != b"PK\x03\x04":
        print("Error: Invalid ZIP signature at detected offset.")
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

    exe_data[zip_offset:zip_offset + zip_size] = new_zip_bytes_padded

    # 5. Write back
    print("Writing modified data to language_server.exe...")
    with open(LS_PATH, "wb") as f:
        f.write(exe_data)
    print("language_server.exe patched successfully.")

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
            print("Note: The active agent backend session remains alive. The changes will take effect when the app is restarted.")
    except Exception as e:
        print(f"\nAn error occurred during patching: {e}")
        if not args.dry_run:
            print("Restoring backups...")
            rollback()
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
