#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import sqlite3
import shutil
import time
import sys
import zipfile
import urllib.request
import ssl
import ctypes
import tempfile
import winreg
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 0. 檢查並提升為系統管理員權限
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        print("🛡️ 正在請求系統管理員權限... (請按「是」允許)")
        script = os.path.abspath(sys.argv[0])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, script, None, 1)
        sys.exit()

run_as_admin()

# ==========================================
# 0.1 自動安裝 Python 套件
# ==========================================
def auto_install_pip_packages():
    required = ['pillow', 'pillow-heif']
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            print(f"📦 正在自動安裝 {pkg} ...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

auto_install_pip_packages()

try:
    from PIL import Image
    from pillow_heif import register_heif_opener
    register_heif_opener()
    CAN_CONVERT = True
except:
    CAN_CONVERT = False

# ==========================================
# 0.2 全自動 Apple 驅動處理（含服務啟動判斷）
# ==========================================
def is_apple_service_installed():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Apple Mobile Device Service")
        winreg.CloseKey(key)
        return True
    except WindowsError:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services")
            i = 0
            while True:
                try:
                    subkey = winreg.EnumKey(key, i)
                    if "Apple" in subkey and "Mobile" in subkey:
                        winreg.CloseKey(key)
                        return True
                    i += 1
                except WindowsError:
                    break
            winreg.CloseKey(key)
        except:
            pass
    return False

def find_apple_service_name():
    try:
        result = subprocess.run(["sc", "query", "type=", "service"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "SERVICE_NAME:" in line and "Apple" in line and "Mobile" in line:
                return line.split(":")[1].strip()
    except:
        pass
    for name in ["Apple Mobile Device Service", "Apple Mobile Device Service (AMD64)"]:
        try:
            subprocess.run(["sc", "query", name], capture_output=True, check=True)
            return name
        except:
            continue
    return None

def start_apple_service():
    service = find_apple_service_name()
    if not service:
        return False
    print(f"🔄 正在啟動服務: {service}")
    try:
        subprocess.run(["net", "start", service], capture_output=True, check=True)
        print("✅ 服務啟動成功。")
        return True
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode('big5', errors='ignore')
        if "已經啟動" in err_msg or "already been started" in err_msg or "2182" in err_msg:
            print("✅ 服務已經在運行。")
            return True
        else:
            print(f"⚠️ 啟動失敗，錯誤: {err_msg}")
            return False

def install_apple_driver_with_winget():
    winget = shutil.which("winget")
    if not winget:
        print("⚠️ winget 未安裝。")
        return False
    print("📦 使用 winget 安裝 Apple Mobile Device Support（最多等待5分鐘）...")
    try:
        cmd = [winget, "install", "-e", "--id", "Apple.AppleMobileDeviceSupport", "--silent", "--accept-package-agreements"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("\n✅ winget 安裝成功。")
            return True
        else:
            print(f"\n⚠️ winget 安裝失敗，錯誤碼 {result.returncode}")
            print(result.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("\n⏱️ winget 安裝超時（5分鐘），將切換到其他方法。")
        return False
    except Exception as e:
        print(f"\n⚠️ winget 異常: {e}")
        return False

def ensure_7z():
    if shutil.which("7z"):
        return True
    print("⬇️ 下載 7-Zip 便攜版...")
    url = "https://www.7-zip.org/a/7zr.exe"
    temp_dir = tempfile.gettempdir()
    sevenz_path = os.path.join(temp_dir, "7zr.exe")
    if os.path.exists(sevenz_path) and os.path.getsize(sevenz_path) > 100 * 1024:
        print("✅ 已存在 7zr.exe")
        os.environ["PATH"] = temp_dir + os.pathsep + os.environ["PATH"]
        return True
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlretrieve(url, sevenz_path, reporthook=lambda a,b,c: print(f"\r下載 7z: {int(a*b*100/c)}%", end=""))
        os.environ["PATH"] = temp_dir + os.pathsep + os.environ["PATH"]
        print("\n✅ 7z 下載完成。")
        return True
    except Exception as e:
        print(f"\n❌ 下載 7z 失敗: {e}")
        return False

def get_official_itunes_url():
    print("🌐 獲取官方 iTunes 下載連結...")
    try:
        url = "https://www.apple.com/itunes/download/win64"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8')
        pattern = r'https://secure-appldnld\.apple\.com/itunes/[^"\']+iTunes64Setup\.exe'
        matches = re.findall(pattern, html)
        if matches:
            print(f"✅ 取得連結: {matches[0]}")
            return matches[0]
        else:
            print("⚠️ 未找到下載連結。")
            return None
    except Exception as e:
        print(f"⚠️ 獲取官方連結失敗: {e}")
        return None

def download_file(url, dest):
    print(f"⬇️ 下載 {os.path.basename(dest)} ...")
    try:
        def report(a, b, c):
            if c > 0:
                print(f"\r下載進度: {int(a*b*100/c)}%", end="")
        urllib.request.urlretrieve(url, dest, reporthook=report)
        print()
        return True
    except Exception as e:
        print(f"\n❌ 下載失敗: {e}")
        return False

def extract_msi_from_itunes_exe(exe_path, dest_dir):
    print("🔧 提取 AppleMobileDeviceSupport64.msi ...")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        cmd = ["7z", "e", exe_path, "-o" + dest_dir, "AppleMobileDeviceSupport64.msi", "-y"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            msi_path = os.path.join(dest_dir, "AppleMobileDeviceSupport64.msi")
            if os.path.exists(msi_path):
                print("✅ 解壓成功。")
                return msi_path
            else:
                print("⚠️ 解壓後未找到 .msi 檔案。")
                return None
        else:
            print(f"⚠️ 7z 解壓失敗: {result.stderr}")
            return None
    except Exception as e:
        print(f"❌ 解壓異常: {e}")
        return None

def install_msi_silent(msi_path):
    print("🔧 正在靜默安裝 Apple Mobile Device Support...")
    try:
        cmd = ["msiexec", "/i", msi_path, "/quiet", "/norestart"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            print("\n✅ 安裝成功。")
            return True
        else:
            print(f"\n⚠️ 安裝失敗，錯誤碼 {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        print("\n⏱️ 安裝超時。")
        return False
    except Exception as e:
        print(f"\n❌ 安裝異常: {e}")
        return False

def install_apple_driver_full():
    if is_apple_service_installed():
        print("✅ Apple 服務已安裝。")
        if start_apple_service():
            return True
        else:
            print("⚠️ 服務啟動失敗，嘗試重新安裝...")

    if install_apple_driver_with_winget():
        time.sleep(5)
        if start_apple_service():
            return True

    print("🔄 嘗試從官方 iTunes 安裝包提取驅動...")
    if not ensure_7z():
        print("❌ 無法取得 7z 工具，放棄。")
        return False

    itunes_url = get_official_itunes_url()
    if not itunes_url:
        print("❌ 無法取得官方下載連結。")
        return False

    temp_dir = tempfile.gettempdir()
    exe_path = os.path.join(temp_dir, "iTunes64Setup.exe")
    if not os.path.exists(exe_path) or os.path.getsize(exe_path) < 100 * 1024 * 1024:
        if not download_file(itunes_url, exe_path):
            return False

    extract_dir = os.path.join(temp_dir, "itunes_extract")
    msi_path = extract_msi_from_itunes_exe(exe_path, extract_dir)
    if not msi_path:
        return False

    if install_msi_silent(msi_path):
        time.sleep(5)
        if start_apple_service():
            return True
        else:
            print("⚠️ 安裝後服務仍無法啟動，請重啟電腦後再試。")
            return False
    else:
        return False

def ensure_apple_driver():
    if not install_apple_driver_full():
        print("\n❌ 自動安裝 Apple 驅動失敗。")
        print("💡 請手動安裝官網 iTunes (https://www.apple.com/tw/itunes/download/win64) 後重啟電腦。")
        sys.exit(1)

# ==========================================
# 1. 自動下載並配置 idevicebackup2
# ==========================================
def ensure_idevicebackup2():
    def is_tool_available(name):
        return shutil.which(name) is not None

    if is_tool_available("idevicebackup2"):
        print("✅ idevicebackup2 已存在。")
        return True

    print("⚠️ 未找到 idevicebackup2，開始自動下載 libimobiledevice 工具...")
    tools_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libimobiledevice")
    bin_dir = os.path.join(tools_dir, "bin")
    os.makedirs(bin_dir, exist_ok=True)

    url = "https://github.com/libimobiledevice-win32/imobiledevice-net/releases/download/v1.3.17/libimobiledevice.1.2.1-r1122-win-x64.zip"
    zip_path = os.path.join(tools_dir, "libimobiledevice.zip")

    if os.path.exists(zip_path) and os.path.getsize(zip_path) > 1024 * 1024:
        print("📁 已存在壓縮檔，跳過下載。")
    else:
        print(f"⬇️ 正在下載 {url} ...")
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
            urllib.request.urlretrieve(url, zip_path)
            print("✅ 下載完成。")
        except Exception as e:
            print(f"❌ 下載失敗: {e}")
            return False

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tools_dir)
        print("✅ 解壓縮完成。")
    except Exception as e:
        print(f"❌ 解壓縮失敗: {e}")
        return False

    exe_path = os.path.join(bin_dir, "idevicebackup2.exe")
    if not os.path.exists(exe_path):
        for root, _, files in os.walk(tools_dir):
            if "idevicebackup2.exe" in files:
                exe_path = os.path.join(root, "idevicebackup2.exe")
                bin_dir = root
                break
        if not os.path.exists(exe_path):
            print("❌ 找不到 idevicebackup2.exe。")
            return False

    os.environ["PATH"] = bin_dir + os.pathsep + os.environ["PATH"]
    print(f"✅ 已將 {bin_dir} 加入 PATH。")
    return True

# ==========================================
# 1.5 自動配對與裝置檢測
# ==========================================
def pair_device():
    """使用 idevicepair 嘗試配對"""
    print("📱 檢查 iPhone 配對狀態...")
    try:
        subprocess.run(["idevicepair", "validate"], capture_output=True, check=True, env=os.environ)
        print("✅ 裝置已配對。")
        return True
    except:
        pass
    print("🔄 嘗試與 iPhone 配對（請確保手機已解鎖並點選「信任」）...")
    try:
        subprocess.run(["idevicepair", "pair"], capture_output=True, check=True, env=os.environ)
        print("✅ 配對成功。")
        return True
    except subprocess.CalledProcessError as e:
        print(f"⚠️ 配對失敗: {e.stderr}")
        return False

def check_device_connected():
    try:
        result = subprocess.run(["idevice_id", "-l"], capture_output=True, text=True, env=os.environ)
        devices = result.stdout.strip().split()
        if devices:
            print(f"✅ 偵測到裝置 UDID: {devices[0]}")
            return True
        else:
            print("❌ 未偵測到任何 iPhone 裝置。")
            return False
    except:
        return False

# ==========================================
# 2. 設定區
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKUP_ROOT = os.path.join(SCRIPT_DIR, "RawBackup")
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_ROOT = os.path.join(SCRIPT_DIR, f"iPhone_Backup_{timestamp}")

for d in [BACKUP_ROOT, OUTPUT_ROOT]:
    os.makedirs(d, exist_ok=True)

# ==========================================
# 3. 備份函式（含自動錯誤處理與重試）
# ==========================================
def run_backup():
    print(f"\n--- 💡 步驟 1: 開始備份 iPhone 至 {BACKUP_ROOT} ---")
    print("📢 請確保手機已解鎖，並在手機上點選『信任此電腦』。")
    print("   若已點選信任，請重新插拔 USB 線後再執行。\n")

    # 先檢查裝置
    if not check_device_connected():
        print("❌ 無法找到 iPhone，請檢查：")
        print("   - 傳輸線是否確實連接")
        print("   - 手機螢幕是否解鎖")
        print("   - 是否已點選『信任此電腦』")
        print("   - 嘗試換一個 USB 埠或重開機")
        return False

    # 嘗試配對
    if not pair_device():
        print("⚠️ 配對失敗，請手動在手機上點選『信任』後重試。")
        return False

    cmd = ["idevicebackup2", "backup", BACKUP_ROOT]
    for attempt in range(1, 4):  # 最多嘗試3次
        if attempt > 1:
            print(f"\n⏳ 等待 5 秒後重試第 {attempt} 次...")
            time.sleep(5)
            # 重試前再次檢查配對
            pair_device()
        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, bufsize=1, encoding='utf-8', errors='replace')
            print("⏳ 備份進行中，請觀察下方進度條...\n")
            output_lines = []
            for line in process.stdout:
                print(line, end='')
                sys.stdout.flush()
                output_lines.append(line)
            process.wait()
            if process.returncode == 0:
                print("\n✅ 備份成功完成！")
                return True
            else:
                # 檢查特定錯誤
                combined = "".join(output_lines)
                if "Could not perform backup protocol version exchange" in combined:
                    print("\n⚠️ 備份協議交換失敗，這通常是手機鎖定或 USB 連線不穩所致。")
                    print("   請確保：")
                    print("   - 手機螢幕保持解鎖且亮著")
                    print("   - 重新插拔 USB 線")
                    print("   - 關閉可能佔用 iPhone 的軟體（如 iTunes、3uTools）")
                    if attempt < 3:
                        print("   將在 5 秒後自動重試...")
                        continue
                    else:
                        print("❌ 多次重試失敗，請手動處理後再執行。")
                        return False
                else:
                    print(f"\n❌ 備份失敗，錯誤代碼: {process.returncode}")
                    return False
        except Exception as e:
            print(f"\n❌ 執行備份時發生錯誤: {e}")
            return False
    return False

# ==========================================
# 4. 輔助函式：保留原始目錄結構
# ==========================================
def get_target_path(rel_path):
    parts = rel_path.split('/')
    if len(parts) > 1:
        relative_without_domain = '/'.join(parts[1:])
    else:
        relative_without_domain = rel_path
    safe_path = os.path.normpath(relative_without_domain)
    return os.path.join(OUTPUT_ROOT, safe_path)

def unique_filename(filepath):
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    base, ext = os.path.splitext(filename)
    counter = 1
    new_name = filename
    while os.path.exists(os.path.join(directory, new_name)):
        new_name = f"{base}_{counter}{ext}"
        counter += 1
    return os.path.join(directory, new_name)

# ==========================================
# 5. 處理單個檔案 (複製 + 轉檔)
# ==========================================
def process_file_task(task):
    src, dst = task
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst):
            return True
        shutil.copy2(src, dst)
        if CAN_CONVERT and dst.upper().endswith(".HEIC"):
            jpg_path = os.path.splitext(dst)[0] + ".jpg"
            if not os.path.exists(jpg_path):
                with Image.open(dst) as img:
                    img.save(jpg_path, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"\n⚠️ 處理 {src} 失敗: {e}")
        return False

# ==========================================
# 6. 校驗函式
# ==========================================
def verify_all_files(tasks):
    print("\n🔍 開始校驗所有檔案是否完整複製...")
    missing = []
    size_mismatch = []
    for src, dst in tasks:
        if not os.path.exists(dst):
            missing.append((src, dst))
        elif os.path.getsize(src) != os.path.getsize(dst):
            size_mismatch.append((src, dst))

    if missing:
        print("\n❌ 以下檔案遺漏未複製:")
        for src, dst in missing:
            print(f"  來源: {src}\n  目標: {dst}\n")
    else:
        print("✅ 所有檔案均已複製（無遺漏）。")

    if size_mismatch:
        print("\n⚠️ 以下檔案大小不符 (可能複製不完整):")
        for src, dst in size_mismatch:
            print(f"  來源: {src} ({os.path.getsize(src)} bytes)\n  目標: {dst} ({os.path.getsize(dst)} bytes)\n")
    else:
        print("✅ 所有複製檔案大小一致。")

    return len(missing) == 0 and len(size_mismatch) == 0

# ==========================================
# 7. 提取主流程
# ==========================================
def extract_and_convert():
    print(f"\n--- 💡 步驟 2: 提取媒體檔案並保留原始目錄結構 ---")
    print(f"📁 輸出資料夾: {OUTPUT_ROOT}")

    subdirs = [d for d in os.listdir(BACKUP_ROOT) if os.path.isdir(os.path.join(BACKUP_ROOT, d))]
    backup_path = None
    for d in subdirs:
        manifest = os.path.join(BACKUP_ROOT, d, "Manifest.db")
        if os.path.exists(manifest):
            backup_path = os.path.join(BACKUP_ROOT, d)
            break

    if not backup_path:
        print("❌ 找不到有效的 Manifest.db，請確認備份是否成功。")
        return

    conn = sqlite3.connect(os.path.join(backup_path, "Manifest.db"))
    cur = conn.cursor()
    query = """
        SELECT fileID, relativePath FROM Files
        WHERE domain IN ('CameraRollDomain', 'MediaDomain')
        AND (
            relativePath LIKE '%.JPG' OR relativePath LIKE '%.JPEG' OR
            relativePath LIKE '%.HEIC' OR relativePath LIKE '%.PNG' OR
            relativePath LIKE '%.MOV' OR relativePath LIKE '%.MP4' OR
            relativePath LIKE '%.M4V' OR
            relativePath LIKE '%.AAE' OR
            relativePath LIKE '%FullSizeRender.jpg' OR
            relativePath LIKE '%FullSizeRender.JPG' OR
            relativePath LIKE '%FullSizeRender.mov' OR
            relativePath LIKE '%FullSizeRender.MOV' OR
            relativePath LIKE '%PenultimateFullSizeRender.jpg' OR
            relativePath LIKE '%PenultimateFullSizeRender.JPG'
        )
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    tasks = []
    for fileID, rel_path in rows:
        src = os.path.join(backup_path, fileID[:2], fileID)
        if not os.path.exists(src):
            continue
        dst_raw = get_target_path(rel_path)
        dst = unique_filename(dst_raw)
        tasks.append((src, dst))

    total = len(tasks)
    print(f"📦 總計偵測到 {total} 個媒體項目。")
    print(f"🚀 正在使用 8 個執行緒同步處理 (複製+轉檔)...")

    done_count = 0
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(process_file_task, task): task for task in tasks}
        for future in as_completed(futures):
            done_count += 1
            percent = (done_count / total) * 100
            print(f"\r📊 目前進度: {percent:.1f}% ({done_count}/{total})", end="", flush=True)

    end_time = time.time()
    print(f"\n\n✨ 提取階段完成！耗時 {int(end_time - start_time)} 秒")
    print(f"📂 成果存放路徑: {OUTPUT_ROOT}")

    verify_all_files(tasks)

# ==========================================
# 8. 主程式入口
# ==========================================
if __name__ == "__main__":
    ensure_apple_driver()
    if not ensure_idevicebackup2():
        print("❌ 無法安裝 libimobiledevice，請手動安裝後再試。")
        sys.exit(1)
    if run_backup():
        extract_and_convert()
    else:
        print("\n⚠️ 備份流程未完成，請檢查連線或磁碟空間後重試。")
        sys.exit(1)