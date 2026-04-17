# iphone_photo_to_window

## How to use
```
copy大量iphone照片&影片到windows電腦

1. 下載 libimobiledevice.1.2.1-r1122-win-x64.zip

2. 解壓後會得到一個資料夾移到：
C:\Program Files\libimobiledevice

3. 加入 PATH（關鍵步驟）

4. 驗證安裝成功(插上 iPhone、解鎖、點「信任」)
//CMD / PowerShell 打：
idevice_id -l
//成功會看到一串類似：
00008110-0012345678901234

5. 再確認備份指令存在
idevicebackup2 --version
where idevicebackup2
看到：
C:\Program Files\libimobiledevice\idevicebackup2.exe

6. 從iphone手機複製照片並且轉檔
【方法New】
python iphone_to_PC_20260417.py

【方法1】
python iphone_to_PC.py

【方法2】
//iphone傳到windows
backup_iphone.py

//windows轉換成可讀photo&video
extract_iphone_media.py

7.【產生結果】
python iphone_to_PC_20260417.py
你的工作目錄/
├── iphone_to_PC.py                    ← 你的 Python 程式
├── RawBackup/                         ← 步驟 1：idevicebackup2 的原始加密備份
│   └── {UDID}/                        ← 每支 iPhone 的唯一識別碼資料夾
│       ├── Manifest.db                ← 備份的檔案索引資料庫
│       ├── Manifest.plist
│       ├── Status.plist
│       ├── Info.plist
│       └── [00..ff]/                  ← 256 個子目錄，存放經 SHA-1 命名的實際檔案片段
│           └── ...
│
└── iPhone_Backup_YYYY-MM-DD_HH-MM-SS/ ← 步驟 2：提取並分類後的媒體檔案（時間為執行當下）
    ├── 1_原始照片/                    ← 所有靜態照片原始檔（.HEIC, .JPG, .PNG）
    ├── 2_影片/                        ← 一般錄影檔案（.MP4, .M4V）
    ├── 3_原況照片影片/                ← 原況照片（Live Photo）的影片部分（.MOV）
    └── 4_編輯後照片/                  ← 你在 iPhone 上編輯過的照片成品
                                        （包含 FullSizeRender.jpg、.AAE 參數檔及對應的編輯後影片）

📝 各資料夾內容說明
資料夾	內容
RawBackup/	idevicebackup2 產生的原始 iOS 加密備份，無法直接用看圖軟體開啟。保留此資料夾可作為完整備份，日後若有需要可再次提取其他資料。
iPhone_Backup_時間戳/	實際可用的媒體檔案輸出資料夾，每次執行都會建立一個新的，避免覆蓋舊的備份。
1_原始照片/	從相機膠卷提取的原始最高畫質照片，包含 .HEIC、.JPG、.PNG 等格式。程式會自動為 .HEIC 檔轉存一份 .JPG 副本放在同一資料夾。
2_影片/	從相機膠卷提取的一般錄影檔（例如 .MP4、.M4V）。
3_原況照片影片/	所有 .MOV 檔案都會被歸類在此，包含 Live Photo 的影片部分。若你也有拍攝一般 .MOV 影片，它們也會出現在這裡（因為程式無法自動區分兩者，但你可以手動將一般影片移到 2_影片/）。
4_編輯後照片/	存放你在 iPhone 上裁切、調色、套濾鏡後的成品，檔名格式為 原照片名_FullSizeRender.jpg，同時也會保留編輯參數檔（.AAE）。若有編輯過 Live Photo，對應的編輯後影片（FullSizeRender.mov）也會在此。
💡 補充提醒
原況照片的靜態照片（.HEIC 或 .JPG）仍然放在 1_原始照片/，與它的影片（.MOV）是分開的。這是因為 iOS 系統本身就是分開儲存這兩個檔案。
若不同資料夾中有完全相同的檔名（例如多個 IMG_0001.HEIC），程式會自動在檔名後方加上 _1、_2 等序號，確保沒有任何檔案被覆蓋遺失。
每次執行都會產生一個全新的輸出資料夾，舊的備份不會被刪除，方便你保留不同時間點的備份版本。

📝 你可能會看到的「不同版本」（非重複，而是不同內容）
檔案類型	存放位置	說明
1.原始照片 .HEIC	1_原始照片/	從相機拍攝的原始檔，未經編輯。
2.HEIC 轉出的 .JPG 副本	1_原始照片/	程式為了方便你在 Windows 上直接預覽而額外產生的轉檔副本，與 .HEIC 內容相同但格式不同。
3.編輯後的照片成品	4_編輯後照片/	若你曾在 iPhone 上編輯過該照片（裁切、調色），系統會另外產生 FullSizeRender.jpg，內容與原始檔不同（已套用編輯效果）。
4.編輯參數檔 .AAE	4_編輯後照片/	記錄編輯步驟的小檔案，非圖片，保留以便日後還原編輯。
5.原況照片的靜態圖	1_原始照片/	原況照片的「封面靜態圖」，通常為 .HEIC。
6.原況照片的影片部分	3_原況照片影片/	原況照片拍攝前後 1.5 秒的動態影片，與靜態圖為兩個獨立檔案，彼此配對。

📝 舉例說明
假設你在 iPhone 上拍了一張原況照片（檔名 IMG_1234），並在手機上編輯過它。
執行腳本後，你會得到以下檔案：
iPhone_Backup_2026-04-18_14-30-00/
├── 1_原始照片/
│   ├── IMG_1234.HEIC          ← 原始靜態圖
│   └── IMG_1234.jpg           ← 自動轉出的預覽用 JPG（內容同 HEIC）
├── 3_原況照片影片/
│   └── IMG_1234.MOV           ← 原況影片（與靜態圖配對）
└── 4_編輯後照片/
    ├── IMG_1234_FullSizeRender.jpg   ← 編輯後的成品（已裁切/調色）
    └── IMG_1234.AAE                  ← 編輯步驟參數
這 不是重複，而是同一張照片的 三個不同狀態（原始、編輯前影片、編輯後成品）。這樣的設計能讓你完整保留所有版本，日後可以自由選擇要保留哪一個。
```
