# iphone_photo_to_window

## How to use
```
// 用系統管理員執行
python iphone_to_PC.py

// 轉換失敗的重新轉換
retry_failed_copy.py

D:\iPhone_Backup_2026-08-19_00-16-54/
│
├── 🗂️ PhotoData/   # 【總倉庫】所有照片、影片、編輯檔案的根目錄
│   │
│   ├── 📁 DCIM/    # 【原始相機膠卷】標準拍照/錄影檔案 (如果有的話)
│   │   └── 📁 100APPLE/   # (或其他序號資料夾)
│   │       ├── 🖼️ IMG_0001.HEIC      # ✅ 原始拍攝的相片 (高畫質)
│   │       ├── 🖼️ IMG_0002.JPG       # ✅ 原始拍攝的相片
│   │       ├── 🎬 IMG_0003.MOV       # ✅ 原始拍攝的影片
│   │       ├── 🎬 IMG_0004.MP4       # ✅ 原始拍攝的影片
│   │       └── ... (其餘原始照片與影片)
│   │
│   ├── 📁 internal/  # 【系統內部處理區】存放編輯中、人像模式的特效暫存檔
│   │   │
│   │   └── 📁 photosmessagesbackdropdescriptors/   # 📸 【人像/去背照片專區】
│   │       │
│   │       ├── 📁 FeaturedPhoto_D42D42AB-BD20-4F4A-9C14-075BD75ACE96/  # (原 `|` 已自動轉為 `_`)
│   │       │   └── 📁 4CAD3C39-D39D-4C33-9460-1DE7370D1E09/   # 該張照片的編輯序號
│   │       │       ├── 📁 output.layerStack/   # 🌟【最終成品（去背/景深照）在這裡！】
│   │       │       │   └── 🖼️ portrait-layer_background.HEIC   # ✅ 套用景深/去背後的最終照片
│   │       │       │
│   │       │       └── 📁 input.segmentation/  # 📝【編輯素材/暫存檔在這裡！】
│   │       │           └── 📁 asset.resource/
│   │       │               ├── 🖼️ proxy.heic     # 預覽用小縮圖 (通常幾十KB，可忽略)
│   │       │               └── 🖼️ Adjusted.JPG   # 編輯過程中的過渡檔案
│   │       │
│   │       ├── 📁 FeaturedPhoto_6BAB7471-7BAB-4EED-98EE-17656030B1E6/   # 第二張特色照片
│   │       │   └── 📁 4D6B0DF7-9E89-43C2-A964-AD94D066E0E5/
│   │       │       ├── 📁 output.layerStack/
│   │       │       │   └── 🖼️ portrait-layer_background.HEIC   # ✅ 第二張成品
│   │       │       └── 📁 input.segmentation/
│   │       │           └── 📁 asset.resource/
│   │       │               ├── 🖼️ proxy.heic
│   │       │               └── 🖼️ Adjusted.JPG
│   │       │
│   │       └── ... (其餘 315 個剛才補救成功的特色照片資料夾)
│   │
│   └── 📁 thumbnails/   # 【縮圖快取】極小的預覽圖 (通常不需理會，可忽略)
│
└── (無其他檔案，因為本腳本只專注於照片與影片提取)

```
