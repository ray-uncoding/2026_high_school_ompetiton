"""
HSV 顏色範圍調校工具
透過 Trackbar 動態調整 HSV 上下界，即時預覽遮罩效果。
將調好的數值填回 color_ball_detector.py 的 COLOR_RANGES。
"""

import cv2
import numpy as np

CAMERA_INDEX = 0


def nothing(x):
    pass


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] 無法開啟攝影機")
        return

    cv2.namedWindow("HSV Tuner")
    cv2.createTrackbar("H Min", "HSV Tuner", 0, 179, nothing)
    cv2.createTrackbar("H Max", "HSV Tuner", 179, 179, nothing)
    cv2.createTrackbar("S Min", "HSV Tuner", 50, 255, nothing)
    cv2.createTrackbar("S Max", "HSV Tuner", 255, 255, nothing)
    cv2.createTrackbar("V Min", "HSV Tuner", 50, 255, nothing)
    cv2.createTrackbar("V Max", "HSV Tuner", 255, 255, nothing)

    print("=" * 40)
    print("  HSV 調校工具")
    print("  拖動滑桿調整範圍")
    print("  按 p 印出目前數值")
    print("  按 q 離開")
    print("=" * 40)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv = cv2.GaussianBlur(hsv, (11, 11), 0)

        h_min = cv2.getTrackbarPos("H Min", "HSV Tuner")
        h_max = cv2.getTrackbarPos("H Max", "HSV Tuner")
        s_min = cv2.getTrackbarPos("S Min", "HSV Tuner")
        s_max = cv2.getTrackbarPos("S Max", "HSV Tuner")
        v_min = cv2.getTrackbarPos("V Min", "HSV Tuner")
        v_max = cv2.getTrackbarPos("V Max", "HSV Tuner")

        lower = np.array([h_min, s_min, v_min])
        upper = np.array([h_max, s_max, v_max])

        mask = cv2.inRange(hsv, lower, upper)
        result = cv2.bitwise_and(frame, frame, mask=mask)

        # 顯示數值在畫面上
        text = f"H:[{h_min}-{h_max}] S:[{s_min}-{s_max}] V:[{v_min}-{v_max}]"
        cv2.putText(result, text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        cv2.imshow("Original", frame)
        cv2.imshow("HSV Tuner", result)
        cv2.imshow("Mask", mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("p"):
            print(f'\n"lower": np.array([{h_min}, {s_min}, {v_min}]),')
            print(f'"upper": np.array([{h_max}, {s_max}, {v_max}])')

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
