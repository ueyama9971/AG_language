import argparse
import os
import sys
import subprocess
import zipfile
import io
import shutil
import struct
import time
import zlib

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


# Translation mappings for the Electron Shell Wizard (wizardHtml.js)
WIZARD_TRANSLATIONS = {
    "Welcome to the new Antigravity!": "新しい Antigravity へようこそ！",
    "Antigravity has been redesigned to put agents first with new capabilities. If you'd still like a code editor, you can download it as a separate app named <b>Antigravity IDE</b>.": "Antigravityはエージェントを第一に考えるように再設計されました。もしエディタ版を引き続き使用したい場合は、個別アプリ「Antigravity IDE」をダウンロードできます。",
    "Download the Antigravity IDE": "Antigravity IDE をダウンロードする",
    "Explore the new Antigravity": "新しい Antigravity を使ってみる"
}

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


def extract_translation_keys():
    """i18n_runtime.js から翻訳キー（英語文字列）を抽出する。"""
    import json
    runtime = load_i18n_runtime()
    start = runtime.find("var T={")
    if start == -1:
        return []
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
        return list(table.keys())
    except json.JSONDecodeError:
        return []


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

def _patch_main_js_inplace(region_data, zip_offset_in_region, zip_size, js_content_bytes):
    """ZIP内のmain.jsの圧縮データだけをin-placeで差し替える（他のファイル・Goデータに触れない）。"""
    data = bytearray(region_data)
    zip_data = bytes(data[zip_offset_in_region:zip_offset_in_region + zip_size])

    in_zip = zipfile.ZipFile(io.BytesIO(zip_data))

    # main.jsのローカルファイルヘッダーを探す
    main_info = None
    for info in in_zip.infolist():
        if info.filename == "main.js":
            main_info = info
            break
    if main_info is None:
        raise ValueError("main.js not found in ZIP")

    # ローカルファイルヘッダーを解析してデータオフセットを特定
    local_header_offset = main_info.header_offset
    abs_local = zip_offset_in_region + local_header_offset
    (_sig, _ver, _flags, _method, _time, _date, _crc,
     comp_size, uncomp_size, fname_len, extra_len
    ) = struct.unpack_from("<IHHHHHIIIHH", data, abs_local)
    data_start = abs_local + 30 + fname_len + extra_len

    # 新しい圧縮データを生成
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    new_compressed = co.compress(js_content_bytes) + co.flush()
    new_crc = zlib.crc32(js_content_bytes) & 0xFFFFFFFF
    new_uncomp = len(js_content_bytes)

    if len(new_compressed) > comp_size:
        raise ValueError(
            f"Recompressed main.js ({len(new_compressed)}) is larger than original ({comp_size}). "
            "Cannot patch in-place."
        )

    print(f"  main.js: original compressed={comp_size}, new compressed={len(new_compressed)}, "
          f"saved={comp_size - len(new_compressed)} bytes")

    # 圧縮データをin-placeで書き込み（余剰バイトはそのまま残る＝ZIPリーダーは無視する）
    data[data_start:data_start + len(new_compressed)] = new_compressed

    # ローカルファイルヘッダーのCRC・サイズを更新
    struct.pack_into("<I", data, abs_local + 14, new_crc)
    struct.pack_into("<I", data, abs_local + 18, len(new_compressed))
    struct.pack_into("<I", data, abs_local + 22, new_uncomp)

    # セントラルディレクトリのmain.jsエントリも更新
    # Go embedded ZIPはコンカテネート型: cd_offsetにconcat調整が必要
    eocd_sig = b"PK\x05\x06"
    eocd_pos = zip_data.rfind(eocd_sig)
    (_esig, _edisk, _ecdisk, _eentriesthis, _eentriestotal,
     cd_size, cd_offset_raw, comment_len) = struct.unpack_from("<IHHHHIIH", zip_data, eocd_pos)
    concat = zip_size - cd_offset_raw - cd_size - 22 - comment_len
    actual_cd_offset = cd_offset_raw + concat

    cd_abs_start = zip_offset_in_region + actual_cd_offset
    pos = cd_abs_start
    cd_end = cd_abs_start + cd_size
    while pos < cd_end:
        sig = struct.unpack_from("<I", data, pos)[0]
        if sig != 0x02014b50:
            break
        cd_fname_len = struct.unpack_from("<H", data, pos + 28)[0]
        cd_extra_len = struct.unpack_from("<H", data, pos + 30)[0]
        cd_comment_len = struct.unpack_from("<H", data, pos + 32)[0]
        cd_fname = data[pos + 46:pos + 46 + cd_fname_len]
        if cd_fname == b"main.js":
            struct.pack_into("<I", data, pos + 16, new_crc)
            struct.pack_into("<I", data, pos + 20, len(new_compressed))
            struct.pack_into("<I", data, pos + 24, new_uncomp)
            print("  Central directory entry for main.js updated.")
            break
        pos += 46 + cd_fname_len + cd_extra_len + cd_comment_len

    return bytes(data)

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
        injected = inject_i18n_runtime(js_text)
        injected_bytes = injected.encode("utf-8")
        co = zlib.compressobj(9, zlib.DEFLATED, -15)
        test_compressed = co.compress(injected_bytes) + co.flush()
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
