# OpenCV 顏色小球偵測 + Arduino 夾爪控制

## 專案架構

```
├── color_ball_detector.py       # Python 主程式（OpenCV 偵測 + 序列通訊）
├── arduino_gripper/
│   └── arduino_gripper.ino      # Arduino 夾爪控制韌體
├── hsv_tuner.py                 # HSV 顏色範圍調校工具
└── README.md
```

## 硬體需求

| 元件 | 說明 |
|------|------|
| Arduino UNO / Nano | 主控板 |
| SG90 伺服馬達 x3 | 夾爪 + X 軸 + Y 軸 |
| USB 攝影機 | 影像擷取 |
| 機械夾爪套件 | 搭配伺服馬達 |
| USB 傳輸線 | Arduino 與電腦連接 |

## 接線圖

```
Arduino Pin 9  -> 夾爪伺服馬達（信號線）
Arduino Pin 10 -> X 軸伺服馬達（信號線）
Arduino Pin 11 -> Y 軸伺服馬達（信號線）
Arduino 5V     -> 伺服馬達 VCC（若電流不足請外接電源）
Arduino GND    -> 伺服馬達 GND
```

> **注意**：3 顆伺服馬達同時運作時，Arduino USB 供電可能不足，建議使用外接 5V 電源供應器。

## 安裝 Python 套件

```bash
pip install opencv-python numpy pyserial
```

## 使用步驟

### 1. 燒錄 Arduino 程式

用 Arduino IDE 開啟 `arduino_gripper/arduino_gripper.ino`，選擇正確的板子與序列埠，上傳。

### 2. 調校 HSV 顏色範圍

先執行 HSV 調校工具，找到目標顏色的最佳範圍：

```bash
python hsv_tuner.py
```

拖動 trackbar 直到 Mask 畫面中只剩目標小球為白色，記下數值後填入 `color_ball_detector.py` 的 `COLOR_RANGES`。

### 3. 修改設定

開啟 `color_ball_detector.py`，修改：

```python
SERIAL_PORT = "COM3"      # 改成你的 Arduino 序列埠
CAMERA_INDEX = 0           # 攝影機編號
TARGET_COLOR = "red"       # 預設偵測顏色
```

### 4. 執行主程式

```bash
python color_ball_detector.py
```

## 操作按鍵

| 按鍵 | 功能 |
|------|------|
| `1` | 偵測紅色 |
| `2` | 偵測藍色 |
| `3` | 偵測綠色 |
| `4` | 偵測黃色 |
| `g` | 手動夾取 |
| `r` | 手動釋放 |
| `a` | 自動夾取模式開關 |
| `q` / `ESC` | 離開 |

## 通訊協定

Python -> Arduino（Serial 9600 baud）：

| 指令 | 說明 |
|------|------|
| `G` | 夾取 |
| `R` | 釋放 |
| `L` | 左移 |
| `H` | 右移 |
| `U` | 上移 |
| `D` | 下移 |
| `C` | 回中心 |
| `X,Y` | 傳送目標座標（自動追蹤） |

Arduino -> Python 回應：

| 回應 | 說明 |
|------|------|
| `OK:GRAB` | 夾取完成 |
| `OK:RELEASE` | 釋放完成 |
| `POS:X,Y` | 目前伺服馬達角度 |

## 運作流程

```
攝影機擷取影像
      ↓
OpenCV HSV 轉換 + 顏色過濾
      ↓
形態學處理（去雜訊）
      ↓
輪廓偵測 → 找到圓形物體
      ↓
計算球心座標
      ↓
判斷：球是否在夾取區域？
    ├─ 否 → 傳送座標給 Arduino → 伺服馬達調整位置
    └─ 是 → 傳送夾取指令 → 夾爪閉合
```
