import subprocess
import os
import sqlite3
import shutil
import time
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
# 1. 設定區 (統一指向外接硬碟 G 槽)
# ==========================================
EXTERNAL_DRIVE = r"G:\iPhone_Data_Transfer"
BACKUP_ROOT = os.path.join(EXTERNAL_DRIVE, "RawBackup")       # 原始備份存放處
DEST_MEDIA = os.path.join(EXTERNAL_DRIVE, "Photos_and_Videos") # 轉檔後照片影片存放處

os.makedirs(BACKUP_ROOT, exist_ok=True)
os.makedirs(DEST_MEDIA, exist_ok=True)

# ==========================================
# 2. 備份函式 (步驟 1)
# ==========================================
def run_backup():
    print(f"--- 💡 步驟 1: 開始備份 iPhone 至 {BACKUP_ROOT} ---")
    print("📢 請確保手機已解鎖，若有『信任此電腦』請點選。")
    
    cmd = ["idevicebackup2", "backup", BACKUP_ROOT]
    try:
        # 直接執行，讓 idevicebackup2 的原生 [====] 進度條顯示在螢幕上
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
# 3. 處理工 (搬運 + 轉檔任務)
# ==========================================
def process_file_task(task):
    """處理單個檔案：複製原始檔 + 若為 HEIC 則轉存一份 JPG"""
    src, dst = task
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # A. 複製原始檔 (保持原始品質與原況照片 MOV)
        # 若檔案已存在且大小相同則跳過，節省二次執行的時間
        if not (os.path.exists(dst) and os.path.getsize(src) == os.path.getsize(dst)):
            shutil.copy2(src, dst)
        
        # B. 轉檔邏輯 (HEIC -> JPG)
        if CAN_CONVERT and dst.upper().endswith(".HEIC"):
            jpg_path = os.path.splitext(dst)[0] + ".jpg"
            if not os.path.exists(jpg_path):
                with Image.open(dst) as img:
                    # 以 90% 品質轉存，兼顧畫質與檔案大小
                    img.save(jpg_path, "JPEG", quality=90)
        return True
    except:
        return False

# ==========================================
# 4. 提取與進度顯示 (步驟 2)
# ==========================================
def extract_and_convert():
    print(f"\n--- 💡 步驟 2: 啟動加速提取與自動轉檔 ---")
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
        AND (relativePath LIKE '%.JPG' OR relativePath LIKE '%.HEIC' OR 
             relativePath LIKE '%.PNG' OR relativePath LIKE '%.MOV' OR 
             relativePath LIKE '%.MP4' OR relativePath LIKE '%.AAE')
    """
    cur.execute(query)
    rows = cur.fetchall()
    conn.close()

    # 準備任務清單 (過濾掉不存在的原始檔)
    tasks = []
    for fileID, rel_path in rows:
        src = os.path.join(backup_path, fileID[:2], fileID)
        dst = os.path.join(DEST_MEDIA, rel_path.replace("/", os.sep))
        if os.path.exists(src):
            tasks.append((src, dst))
    
    total = len(tasks)
    print(f"📦 總計偵測到 {total} 個媒體項目。")
    print(f"🚀 正在使用 8 個執行緒同步處理 (複製+轉檔)...")

    # --- 使用 ThreadPoolExecutor 平行處理並顯示百分比 ---
    done_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=8) as executor:
        # 提交所有任務
        futures = {executor.submit(process_file_task, task): task for task in tasks}
        
        # 當任一任務完成時回傳
        for future in as_completed(futures):
            done_count += 1
            percent = (done_count / total) * 100
            # 即時刷新同一行的進度顯示
            print(f"\r📊 目前進度: {percent:.1f}% ({done_count}/{total})", end="", flush=True)

    end_time = time.time()
    print(f"\n\n✨ 任務圓滿完成！")
    print(f"⏱️  總提取與轉檔耗時: {int(end_time - start_time)} 秒")
    print(f"📂 成果存放路徑: {DEST_MEDIA}")

# ==========================================
# 5. 主程式入口
# ==========================================
if __name__ == "__main__":
    # 流程：備份 -> 成功後自動提取轉檔
    if run_backup():
        extract_and_convert()
    else:
        print("\n⚠️ 備份流程未完成，請檢查連線或磁碟空間後重試。")