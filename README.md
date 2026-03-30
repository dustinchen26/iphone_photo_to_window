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
【方法1】
python iphone_to_PC.py

【方法2】
//iphone傳到windows
backup_iphone.py

//windows轉換成可讀photo&video
extract_iphone_media.py
```
