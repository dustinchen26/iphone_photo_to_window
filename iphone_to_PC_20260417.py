import subprocess
import os
import sqlite3
import shutil
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 嘗試引入轉檔工具，若未安裝則只進行提取不轉檔
try:
    from PIL import Image
    from pillow_heif import register_heif_opener
    register_heif_opener()
    CAN_CONVERT = True
except ImportError:
    CAN_CONVERT = False

# ==========================================
# 1. 設定區 (自動以腳本所在目錄為基準)
# ==========================================
# 取得目前這個 .py 檔案所在的資料夾絕對路徑
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 原始備份存放處 (在腳本目錄下建立 RawBackup 資料夾)
BACKUP_ROOT = os.path.join(SCRIPT_DIR, "RawBackup")

# 以執行當下的時間建立輸出資料夾名稱
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
OUTPUT_ROOT = os.path.join(SCRIPT_DIR, f"iPhone_Backup_{timestamp}")

# 四個分類子目錄
DIR_PHOTOS = os.path.join(OUTPUT_ROOT, "1_原始照片")
DIR_VIDEOS = os.path.join(OUTPUT_ROOT, "2_影片")
DIR_LIVE_PHOTO_VIDEOS = os.path.join(OUTPUT_ROOT, "3_原況照片影片")
DIR_EDITED = os.path.join(OUTPUT_ROOT, "4_編輯後照片")

# 建立所有需要的目錄
for d in [BACKUP_ROOT, OUTPUT_ROOT, DIR_PHOTOS, DIR_VIDEOS, DIR_LIVE_PHOTO_VIDEOS, DIR_EDITED]:
    os.makedirs(d, exist_ok=True)

# ==========================================
# 2. 備份函式 (步驟 1)
# ==========================================
def run_backup():
    print(f"--- 💡 步驟 1: 開始備份 iPhone 至 {BACKUP_ROOT} ---")
    print("📢 請確保手機已解鎖，若有『信任此電腦』請點選。")
    
    cmd = ["idevicebackup2", "backup", BACKUP_ROOT]
    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            print("\n✅ 備份成功完成！")
            return True
        else:
            print(f"\n❌ 備份失敗，錯誤代碼: {result.returncode}")
            return False
    except Exception as e:
        print(f"\n❌ 執行備份時發生錯誤: {e}")
        return False

# ==========================================
# 3. 輔助函式：決定輸出檔名與分類目錄
# ==========================================
def get_output_info(rel_path):
    """
    根據 iOS 備份內的相對路徑，回傳 (目標子目錄, 最終檔名)
    """
    norm_path = rel_path.replace("/", os.sep)
    parts = norm_path.split(os.sep)
    filename = parts[-1]
    base, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    # ----- 判斷是否為編輯後的照片 -----
    if "Mutations" in parts and "Adjustments" in parts:
        try:
            idx = parts.index("Adjustments")
            original_name = parts[idx-1] if idx >= 1 else "edited"
        except ValueError:
            original_name = "edited"
        
        new_name = f"{original_name}_{base}{ext}"
        return DIR_EDITED, new_name

    # ----- 判斷是否為原況照片的影片部分 (.MOV) -----
    if ext_lower == ".mov":
        return DIR_LIVE_PHOTO_VIDEOS, filename

    # ----- 一般影片檔 (MP4 等) -----
    if ext_lower in [".mp4", ".m4v"]:
        return DIR_VIDEOS, filename

    # ----- 編輯參數檔 .AAE -----
    if ext_lower == ".aae":
        return DIR_EDITED, filename

    # ----- 其餘皆視為靜態照片 (JPG, HEIC, PNG) -----
    return DIR_PHOTOS, filename

def unique_filename(directory, filename):
    """
    若檔案已存在，自動在檔名後加上 _1, _2 等序號。
    """
    base, ext = os.path.splitext(filename)
    counter = 1
    new_name = filename
    while os.path.exists(os.path.join(directory, new_name)):
        new_name = f"{base}_{counter}{ext}"
        counter += 1
    return new_name

# ==========================================
# 4. 處理工作 (搬運 + 轉檔任務)
# ==========================================
def process_file_task(task):
    """處理單個檔案：複製到對應分類資料夾 + 若為 HEIC 則轉存一份 JPG"""
    src, dst = task
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # A. 複製原始檔
        if not (os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst)):
            shutil.copy2(src, dst)
        
        # B. 轉檔邏輯 (HEIC -> JPG)
        if CAN_CONVERT and dst.upper().endswith(".HEIC"):
            jpg_path = os.path.splitext(dst)[0] + ".jpg"
            if not os.path.exists(jpg_path):
                with Image.open(dst) as img:
                    img.save(jpg_path, "JPEG", quality=90)
        return True
    except:
        return False

# ==========================================
# 5. 提取與進度顯示 (步驟 2)
# ==========================================
def extract_and_convert():
    print(f"\n--- 💡 步驟 2: 啟動加速提取與自動轉檔 ---")
    print(f"📁 輸出資料夾: {OUTPUT_ROOT}")
    if not CAN_CONVERT:
        print("⚠️  未偵測到 pillow-heif，將僅提取原始檔，不進行 JPG 轉檔。")

    # 搜尋備份資料夾 (UDID)
    subdirs = [d for d in os.listdir(BACKUP_ROOT) if os.path.isdir(os.path.join(BACKUP_ROOT, d))]
    backup_path = next((os.path.join(BACKUP_ROOT, d) for d in subdirs if os.path.exists(os.path.join(BACKUP_ROOT, d, "Manifest.db"))), None)
    
    if not backup_path:
        print("❌ 找不到有效的 Manifest.db，請確認備份是否成功。")
        return

    # 從資料庫撈取檔案清單
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
        
        target_dir, final_filename = get_output_info(rel_path)
        final_filename = unique_filename(target_dir, final_filename)
        dst = os.path.join(target_dir, final_filename)
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
    print(f"\n\n✨ 任務圓滿完成！")
    print(f"⏱️  總提取與轉檔耗時: {int(end_time - start_time)} 秒")
    print(f"📂 成果存放路徑: {OUTPUT_ROOT}")
    print(f"   ├── 1_原始照片")
    print(f"   ├── 2_影片")
    print(f"   ├── 3_原況照片影片")
    print(f"   └── 4_編輯後照片")

# ==========================================
# 6. 主程式入口
# ==========================================
if __name__ == "__main__":
    if run_backup():
        extract_and_convert()
    else:
        print("\n⚠️ 備份流程未完成，請檢查連線或磁碟空間後重試。")