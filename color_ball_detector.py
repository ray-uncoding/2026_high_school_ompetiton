"""
OpenCV 顏色小球偵測 + Arduino 夾爪控制
透過攝影機偵測指定顏色的小球，計算其位置，並透過序列埠傳送指令給 Arduino 控制夾爪。
"""

import cv2
import numpy as np
import serial
import time
import sys

# ===== 設定區 =====

# Arduino 序列埠設定（請依照實際狀況修改）
SERIAL_PORT = "COM3"
SERIAL_BAUD = 9600

# 攝影機編號（0 = 預設攝影機）
CAMERA_INDEX = 0

# 畫面尺寸
FRAME_WIDTH = 640
FRAME_HEIGHT = 480

# 小球最小面積（像素），過濾雜訊用
MIN_CONTOUR_AREA = 500

# HSV 顏色範圍設定（可透過 trackbar 動態調整）
# 預設為紅色小球（紅色在 HSV 中跨越 0 度，需要兩組範圍）
COLOR_RANGES = {
    "red": [
        {"lower": np.array([0, 120, 70]), "upper": np.array([10, 255, 255])},
        {"lower": np.array([170, 120, 70]), "upper": np.array([180, 255, 255])},
    ],
    "blue": [
        {"lower": np.array([100, 150, 50]), "upper": np.array([130, 255, 255])},
    ],
    "green": [
        {"lower": np.array([35, 100, 50]), "upper": np.array([85, 255, 255])},
    ],
    "yellow": [
        {"lower": np.array([20, 100, 100]), "upper": np.array([35, 255, 255])},
    ],
    "orange": [
        {"lower": np.array([0, 133, 155]), "upper": np.array([23, 220, 200])},
    ],
}

# 目前偵測的目標顏色
TARGET_COLOR = "orange"

# 夾取判定區域（畫面中央的範圍，單位：像素）
GRAB_ZONE_X = 50  # 中心左右容許範圍
GRAB_ZONE_Y = 50  # 中心上下容許範圍

# ===== Arduino 通訊協定 =====
# 傳送至 Arduino 的指令格式：
#   "G\n"   -> 夾取（Grab）
#   "R\n"   -> 釋放（Release）
#   "L\n"   -> 左移
#   "H\n"   -> 右移
#   "U\n"   -> 上移
#   "D\n"   -> 下移
#   "C\n"   -> 置中
#   "X,Y\n" -> 傳送目標座標（例如 "320,240\n"）


def init_serial(port, baud):
    """初始化 Arduino 序列埠連線"""
    try:
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)  # 等待 Arduino 重啟
        print(f"[INFO] 已連接 Arduino: {port} @ {baud}")
        return ser
    except serial.SerialException as e:
        print(f"[WARN] 無法連接 Arduino ({port}): {e}")
        print("[WARN] 將以無 Arduino 模式運行（僅顯示畫面）")
        return None


def send_command(ser, cmd):
    """透過序列埠傳送指令給 Arduino"""
    if ser and ser.is_open:
        ser.write(f"{cmd}\n".encode("utf-8"))
        print(f"[CMD] -> Arduino: {cmd}")


def detect_color_ball(frame, color_name):
    """
    在影像中偵測指定顏色的小球
    回傳: list of (x, y, radius) 各偵測到的球心座標與半徑
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 高斯模糊降噪
    hsv = cv2.GaussianBlur(hsv, (11, 11), 0)

    ranges = COLOR_RANGES.get(color_name, [])
    mask = np.zeros(hsv.shape[:2], dtype=np.uint8)

    for r in ranges:
        partial = cv2.inRange(hsv, r["lower"], r["upper"])
        mask = cv2.bitwise_or(mask, partial)

    # 形態學處理：去雜訊 + 填補破洞
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.erode(mask, kernel, iterations=2)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # 尋找輪廓
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    balls = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_CONTOUR_AREA:
            continue

        # 最小外接圓
        ((cx, cy), radius) = cv2.minEnclosingCircle(cnt)
        if radius > 10:
            balls.append((int(cx), int(cy), int(radius)))

    return balls, mask


def draw_overlay(frame, balls, color_name):
    """在畫面上繪製偵測結果與輔助資訊"""
    h, w = frame.shape[:2]
    center_x, center_y = w // 2, h // 2

    # 繪製中央十字線
    cv2.line(frame, (center_x - 30, center_y), (center_x + 30, center_y), (255, 255, 255), 1)
    cv2.line(frame, (center_x, center_y - 30), (center_x, center_y + 30), (255, 255, 255), 1)

    # 繪製夾取判定區域
    cv2.rectangle(
        frame,
        (center_x - GRAB_ZONE_X, center_y - GRAB_ZONE_Y),
        (center_x + GRAB_ZONE_X, center_y + GRAB_ZONE_Y),
        (0, 255, 0), 2
    )

    # 繪製偵測到的球
    color_map = {"red": (0, 0, 255), "blue": (255, 0, 0), "green": (0, 255, 0), "yellow": (0, 255, 255)}
    draw_color = color_map.get(color_name, (255, 255, 255))

    for (cx, cy, r) in balls:
        cv2.circle(frame, (cx, cy), r, draw_color, 2)
        cv2.circle(frame, (cx, cy), 3, (255, 255, 255), -1)
        cv2.putText(frame, f"({cx},{cy})", (cx - 40, cy - r - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, draw_color, 2)

        # 從球心到畫面中央畫箭頭
        cv2.arrowedLine(frame, (center_x, center_y), (cx, cy), (255, 255, 0), 1)

    # 狀態文字
    cv2.putText(frame, f"Color: {color_name}", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Balls: {len(balls)}", (10, 55),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return frame


def is_in_grab_zone(ball_x, ball_y, frame_w, frame_h):
    """判斷球是否在夾取區域內"""
    center_x, center_y = frame_w // 2, frame_h // 2
    return (abs(ball_x - center_x) < GRAB_ZONE_X and
            abs(ball_y - center_y) < GRAB_ZONE_Y)


def main():
    global TARGET_COLOR

    # 初始化序列埠
    ser = init_serial(SERIAL_PORT, SERIAL_BAUD)

    # 初始化攝影機
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("[ERROR] 無法開啟攝影機")
        sys.exit(1)

    print("=" * 50)
    print("  OpenCV 顏色小球偵測 + Arduino 夾爪控制")
    print("=" * 50)
    print("按鍵說明：")
    print("  1/2/3/4 - 切換偵測顏色 (紅/藍/綠/黃)")
    print("  g       - 手動夾取")
    print("  r       - 手動釋放")
    print("  a       - 自動夾取模式開關")
    print("  q/ESC   - 離開程式")
    print("=" * 50)

    auto_grab = False
    grab_cooldown = 0  # 夾取冷卻（避免重複觸發）

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] 讀取影像失敗")
            break

        # 偵測顏色小球
        balls, mask = detect_color_ball(frame, TARGET_COLOR)

        # 繪製覆蓋資訊
        display = draw_overlay(frame.copy(), balls, TARGET_COLOR)

        # 自動夾取邏輯
        if auto_grab and balls and grab_cooldown <= 0:
            # 選擇最大的球（最近的）
            largest = max(balls, key=lambda b: b[2])
            bx, by, br = largest

            if is_in_grab_zone(bx, by, FRAME_WIDTH, FRAME_HEIGHT):
                # 球在夾取區域內 -> 執行夾取
                send_command(ser, "G")
                cv2.putText(display, "GRABBING!", (FRAME_WIDTH // 2 - 80, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                grab_cooldown = 60  # 冷卻 60 幀
            else:
                # 傳送球的座標讓 Arduino 調整位置
                send_command(ser, f"{bx},{by}")

        if grab_cooldown > 0:
            grab_cooldown -= 1
            cv2.putText(display, f"Cooldown: {grab_cooldown}", (10, 85),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 200), 1)

        # 顯示自動模式狀態
        mode_text = "AUTO" if auto_grab else "MANUAL"
        mode_color = (0, 255, 0) if auto_grab else (0, 0, 255)
        cv2.putText(display, mode_text, (FRAME_WIDTH - 120, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, mode_color, 2)

        # 顯示畫面
        cv2.imshow("Ball Detector", display)
        cv2.imshow("Mask", mask)

        # 鍵盤控制
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q") or key == 27:  # q 或 ESC
            break
        elif key == ord("1"):
            TARGET_COLOR = "red"
            print("[INFO] 切換顏色: 紅色")
        elif key == ord("2"):
            TARGET_COLOR = "blue"
            print("[INFO] 切換顏色: 藍色")
        elif key == ord("3"):
            TARGET_COLOR = "green"
            print("[INFO] 切換顏色: 綠色")
        elif key == ord("4"):
            TARGET_COLOR = "yellow"
            print("[INFO] 切換顏色: 黃色")
        elif key == ord("g"):
            send_command(ser, "G")
            print("[INFO] 手動夾取")
        elif key == ord("r"):
            send_command(ser, "R")
            print("[INFO] 手動釋放")
        elif key == ord("a"):
            auto_grab = not auto_grab
            print(f"[INFO] 自動模式: {'ON' if auto_grab else 'OFF'}")

    # 清理資源
    cap.release()
    cv2.destroyAllWindows()
    if ser and ser.is_open:
        ser.close()
        print("[INFO] 已關閉序列埠")
    print("[INFO] 程式結束")


if __name__ == "__main__":
    main()
