import os
import sys
import subprocess
import shutil

# Target Paths for Antigravity IDE
INSTALL_DIR = r"C:\Users\ueyam\AppData\Local\Programs\Antigravity IDE"
PACKAGE_JSON_PATH = os.path.join(INSTALL_DIR, "resources", "app", "extensions", "antigravity", "package.json")
PACKAGE_JSON_BAK = PACKAGE_JSON_PATH + ".bak"
MAIN_JS_PATH = os.path.join(INSTALL_DIR, "resources", "app", "out", "jetskiAgent", "main.js")
MAIN_JS_BAK = MAIN_JS_PATH + ".bak"

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

# Translation mappings for the Extension Commands & Configuration (package.json)
PACKAGE_TRANSLATIONS = {
    '"Log in to IDE"': '"IDEにログイン"',
    '"Provide Auth Token (Backup Login)"': '"認証トークンの入力 (バックアップログイン)"',
    '"Import VS Code settings"': '"VS Codeの設定をインポート"',
    '"Import VS Code extensions"': '"VS Codeの拡張機能をインポート"',
    '"Import VS Code recent workspaces"': '"最近使用したVS Codeワークスペースをインポート"',
    '"Import Cursor settings"': '"Cursorの設定をインポート"',
    '"Import Cursor extensions"': '"Cursorの拡張機能をインポート"',
    '"Import Windsurf settings"': '"Windsurfの設定をインポート"',
    '"Import Windsurf extensions"': '"Windsurfの拡張機能をインポート"',
    '"Generate Commit Message"': '"コミットメッセージを自動生成"',
    '"Restart Language Server"': '"Language Serverを再起動"',
    '"Kill Language Server and Reload Window"': '"Language Serverを停止してウィンドウを再読込"',
    '"Toggle Persistent Language Server and Reload Window"': '"常駐Language Serverの切り替えとウィンドウ再読込"',
    '"Open Persistent Language Server Log"': '"常駐Language Serverログを開く"',
    '"Copy API Key to Clipboard"': '"APIキーをクリップボードにコピー"',
    '"Open Changelog"': '"変更履歴を開く"',
    '"Open Browser"': '"ブラウザを開く"',
    '"Show Browser Allowlist"': '"ブラウザの許可リストを表示"',
    '"Kill Remote Extension Host"': '"リモートの拡張機能ホストを終了"',
    '"Import Cider settings"': '"Ciderの設定をインポート"',
    '"[Beta] Start Demo Mode"': '"[ベータ] デモモードの開始"',
    '"[Beta] End Demo Mode"': '"[ベータ] デモモードの終了"',
    '"Antigravity Editor"': '"Antigravity エディタ設定"',
    '"Keep the Language Server running after the editor is closed."': '"エディタを閉じた後もLanguage Serverを実行し続ける"',
    '"Enable the Cursor-import commands in the palette"': '"コマンドパレットでCursorのインポートコマンドを有効にする"'
}

def terminate_processes():
    print("Terminating running Antigravity IDE processes...")
    try:
        # Stop Antigravity IDE processes by matching their path
        ps_cmd_app = (
            'Get-Process -Name "Antigravity IDE" -ErrorAction SilentlyContinue | '
            'Stop-Process -Force'
        )
        subprocess.run(["powershell", "-Command", ps_cmd_app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("IDE processes terminated.")
    except Exception as e:
        print(f"Warning: Could not terminate processes: {e}")

def create_backups():
    print("Checking and creating backups...")
    if not os.path.exists(PACKAGE_JSON_PATH):
        print(f"Error: package.json not found at {PACKAGE_JSON_PATH}")
        sys.exit(1)
    if not os.path.exists(MAIN_JS_PATH):
        print(f"Error: main.js not found at {MAIN_JS_PATH}")
        sys.exit(1)
        
    if not os.path.exists(PACKAGE_JSON_BAK):
        shutil.copy2(PACKAGE_JSON_PATH, PACKAGE_JSON_BAK)
        print(f"Created backup: {PACKAGE_JSON_BAK}")
    else:
        print(f"Backup already exists: {PACKAGE_JSON_BAK}")
        
    if not os.path.exists(MAIN_JS_BAK):
        shutil.copy2(MAIN_JS_PATH, MAIN_JS_BAK)
        print(f"Created backup: {MAIN_JS_BAK}")
    else:
        print(f"Backup already exists: {MAIN_JS_BAK}")

def rollback():
    print("Rolling back to original backups...")
    if os.path.exists(PACKAGE_JSON_BAK):
        shutil.copy2(PACKAGE_JSON_BAK, PACKAGE_JSON_PATH)
        print(f"Restored: {PACKAGE_JSON_PATH}")
    else:
        print(f"Backup not found: {PACKAGE_JSON_BAK}")
        
    if os.path.exists(MAIN_JS_BAK):
        shutil.copy2(MAIN_JS_BAK, MAIN_JS_PATH)
        print(f"Restored: {MAIN_JS_PATH}")
    else:
        print(f"Backup not found: {MAIN_JS_BAK}")
    print("Rollback complete.")

def patch_package_json():
    print("Patching package.json...")
    with open(PACKAGE_JSON_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    for eng, ja in PACKAGE_TRANSLATIONS.items():
        content = content.replace(eng, ja)
        
    with open(PACKAGE_JSON_PATH, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("package.json patched successfully.")

def patch_main_js():
    print("Patching main.js...")
    with open(MAIN_JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
        
    for eng, ja in UI_TRANSLATIONS.items():
        content = content.replace(eng, ja)
        
    with open(MAIN_JS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("main.js patched successfully.")

def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--rollback":
        terminate_processes()
        rollback()
        return
        
    print("=== Antigravity IDE Japanese Patch ===")
    terminate_processes()
    create_backups()
    
    try:
        patch_package_json()
        patch_main_js()
        print("\nLocalization completed successfully! You can now restart Antigravity IDE.")
    except Exception as e:
        print(f"\nAn error occurred during patching: {e}")
        print("Restoring backups...")
        rollback()

if __name__ == "__main__":
    main()
