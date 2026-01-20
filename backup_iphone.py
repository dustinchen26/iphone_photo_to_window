import subprocess
import os

BACKUP_DIR = r"C:\iPhoneBackup"

os.makedirs(BACKUP_DIR, exist_ok=True)

cmd = [
    "idevicebackup2",
    "backup",
    BACKUP_DIR
]

print("📱 開始完整備份 iPhone（照片＋影片）...")
subprocess.run(cmd, check=True)
print("✅ 備份完成")
