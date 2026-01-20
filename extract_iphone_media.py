import sqlite3
import os
import shutil
import time

# =========================
# 1️⃣ 設定路徑
# =========================
BACKUP_ROOT = r"C:\iPhoneBackup"   # iPhone 備份根目錄
DEST = r"D:\iPhoneMediaOK2"           # 提取後存放資料夾
os.makedirs(DEST, exist_ok=True)

# =========================
# 2️⃣ 找 UDID 目錄
# =========================
udid = next(d for d in os.listdir(BACKUP_ROOT) if d.startswith("0000"))
backup = os.path.join(BACKUP_ROOT, udid)

# =========================
# 3️⃣ 連接 Manifest.db
# =========================
db_path = os.path.join(backup, "Manifest.db")
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# =========================
# 4️⃣ 檢查 tables
# =========================
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
if "Files" not in tables:
    raise RuntimeError("❌ 找不到 Files table")
print("Tables:", tables)

# =========================
# 5️⃣ 查 CameraRollDomain / MediaDomain
# =========================
cur.execute("""
SELECT fileID, relativePath, domain
FROM Files
WHERE domain IN ('CameraRollDomain', 'MediaDomain')
""")
rows = cur.fetchall()
print(f"📸 Found {len(rows)} media files in backup")

ok = 0
skip = 0
fail = 0

# =========================
# 6️⃣ 逐一提取，保留子資料夾結構
# =========================
for fileID, rel_path, domain in rows:
    src = os.path.join(backup, fileID[:2], fileID)
    if not os.path.exists(src):
        skip += 1
        continue

    # 保留原始 DCIM 路徑
    dst = os.path.join(DEST, rel_path.replace("/", os.sep))
    dst_folder = os.path.dirname(dst)
    os.makedirs(dst_folder, exist_ok=True)

    # 避免覆蓋同名檔案
    if os.path.exists(dst):
        base, ext = os.path.splitext(dst)
        i = 1
        while os.path.exists(f"{base}_{i}{ext}"):
            i += 1
        dst = f"{base}_{i}{ext}"

    try:
        shutil.copy2(src, dst)
        ok += 1
    except PermissionError:
        time.sleep(0.05)
        fail += 1
    except Exception as e:
        print("❌ Failed:", src, e)
        fail += 1

print(f"✅ 完成：OK:{ok} Skip:{skip} Fail:{fail}")
