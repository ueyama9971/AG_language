import os
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
ZIP_START_OFFSET = 107141712
ZIP_TARGET_SIZE = 2884187

# Translation mappings for the Agent Web UI (main.js)
UI_TRANSLATIONS = {
    '"Always Ask"': '"常に確認"',
    '"Always Deny"': '"常に拒否"',
    '"Always Allow"': '"常に許可"',
    'title:"Token Usage"': 'title:"トークン使用量"',
    '"App Settings"': '"アプリ設定"',
    'title:c??"Workspace Settings"': 'title:c??"ワークスペース設定"',
    'hideBreakdownForGroups:f=["System Prompt"]': 'hideBreakdownForGroups:f=["システムプロンプト"]',
    'hideBreakdownForGroups:a=["System Prompt"]': 'hideBreakdownForGroups:a=["システムプロンプト"]',
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
    '"Workspace Web Access"': '"ウェブアクセス権限"'
}

# Translation mappings for the Electron Shell Wizard (wizardHtml.js)
WIZARD_TRANSLATIONS = {
    "Welcome to the new Antigravity!": "新しい Antigravity へようこそ！",
    "Antigravity has been redesigned to put agents first with new capabilities. If you'd still like a code editor, you can download it as a separate app named <b>Antigravity IDE</b>.": "Antigravityはエージェントを第一に考えるように再設計されました。もしエディタ版を引き続き使用したい場合は、個別アプリ「Antigravity IDE」をダウンロードできます。",
    "Download the Antigravity IDE": "Antigravity IDE をダウンロードする",
    "Explore the new Antigravity": "新しい Antigravity を使ってみる"
}

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

def patch_asar(temp_dir):
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

def patch_language_server():
    # 1. Rename running binary to release the file path lock
    print("Renaming running language_server.exe to language_server.exe.tmp...")
    if os.path.exists(LS_TMP):
        try:
            os.remove(LS_TMP)
        except Exception as e:
            print(f"Warning: Could not remove old tmp file: {e}")
            
    os.rename(LS_PATH, LS_TMP)
    
    # 2. Read base executable data from the renamed tmp file
    print("Reading base executable from tmp file...")
    with open(LS_TMP, "rb") as f:
        exe_data = bytearray(f.read())
        
    # Extract embedded zip
    zip_bytes = exe_data[ZIP_START_OFFSET:ZIP_START_OFFSET + ZIP_TARGET_SIZE]
    if zip_bytes[:4] != b"PK\x03\x04":
        print("Error: Invalid ZIP signature at offset. Offset mismatch.")
        # Restore original before exiting
        os.rename(LS_TMP, LS_PATH)
        sys.exit(1)
        
    print("Modifying web assets inside the embedded ZIP...")
    in_zip = zipfile.ZipFile(io.BytesIO(zip_bytes))
    out_bio = io.BytesIO()
    
    # Rebuild the ZIP with maximum compression to make sure it remains smaller than target size
    out_zip = zipfile.ZipFile(out_bio, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)
    
    for item in in_zip.infolist():
        data = in_zip.read(item.filename)
        if item.filename == 'main.js':
            js_text = data.decode('utf-8')
            for eng, ja in UI_TRANSLATIONS.items():
                js_text = js_text.replace(eng, ja)
            data = js_text.encode('utf-8')
            
        out_zip.writestr(item, data)
        
    out_zip.close()
    new_zip_bytes = out_bio.getvalue()
    
    print(f"New ZIP size (compressed): {len(new_zip_bytes)} bytes")
    
    # Pad to exact target size
    new_zip_bytes_padded = pad_zip_to_size(new_zip_bytes, ZIP_TARGET_SIZE)
    print(f"Padded ZIP size: {len(new_zip_bytes_padded)} bytes (Target: {ZIP_TARGET_SIZE})")
    
    # Overwrite zip data inside exe
    exe_data[ZIP_START_OFFSET:ZIP_START_OFFSET + ZIP_TARGET_SIZE] = new_zip_bytes_padded
    
    # 3. Write modified data back to the original path (which is now free!)
    print("Writing modified data to language_server.exe...")
    with open(LS_PATH, "wb") as f:
        f.write(exe_data)
        
    print("language_server.exe patched successfully.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        rollback()
        return
        
    print("=== Antigravity 2.0 Standalone Japanese Patch ===")
    terminate_electron_only()
    create_backups()
    
    # Temp dir for ASAR extraction
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_asar")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    try:
        patch_asar(temp_dir)
        patch_language_server()
        print("\nLocalization completed successfully! You can now restart Antigravity.")
        print("Note: The active agent backend session remains alive. The changes will take effect when the app is restarted.")
    except Exception as e:
        print(f"\nAn error occurred during patching: {e}")
        print("Restoring backups...")
        rollback()
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
