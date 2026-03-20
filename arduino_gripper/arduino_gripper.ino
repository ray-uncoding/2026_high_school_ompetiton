/*
 * Arduino 夾爪控制程式
 * 接收來自 Python (OpenCV) 的序列指令，控制伺服馬達夾爪與 XY 軸移動。
 *
 * 硬體接線：
 *   - 夾爪伺服馬達 -> Pin 9
 *   - X 軸伺服馬達 -> Pin 10（水平旋轉）
 *   - Y 軸伺服馬達 -> Pin 11（垂直升降）
 * 
 * 2026-03-20 by ChatGPT
 *
 * 通訊協定（Serial 9600 baud）：
 *   "G"      -> 夾取
 *   "R"      -> 釋放
 *   "L"      -> 左移
 *   "H"      -> 右移（避開與 R:Release 衝突）
 *   "U"      -> 上移
 *   "D"      -> 下移
 *   "C"      -> 回中心位置
 *   "X,Y"    -> 自動根據座標調整位置（例如 "320,240"）
 */

#include <Servo.h>

// ===== 腳位設定 =====
#define GRIPPER_PIN  9    // 夾爪伺服馬達
#define SERVO_X_PIN  10   // X 軸伺服馬達
#define SERVO_Y_PIN  11   // Y 軸伺服馬達

// ===== 夾爪角度 =====
#define GRIPPER_OPEN   90   // 張開角度
#define GRIPPER_CLOSE  30   // 夾緊角度

// ===== XY 軸範圍 =====
#define SERVO_X_MIN  0
#define SERVO_X_MAX  180
#define SERVO_Y_MIN  30
#define SERVO_Y_MAX  150

// ===== 畫面參數（需與 Python 端一致）=====
#define FRAME_WIDTH   640
#define FRAME_HEIGHT  480
#define FRAME_CENTER_X  (FRAME_WIDTH / 2)
#define FRAME_CENTER_Y  (FRAME_HEIGHT / 2)

// ===== 位置調整步進 =====
#define STEP_SIZE  2    // 每次移動的角度
#define DEAD_ZONE  30   // 死區（偏差在此範圍內不動作）

// ===== 全域變數 =====
Servo gripperServo;
Servo servoX;
Servo servoY;

int posX = 90;   // X 軸目前角度
int posY = 90;   // Y 軸目前角度
bool gripperClosed = false;

String inputBuffer = "";

void setup() {
    Serial.begin(9600);

    gripperServo.attach(GRIPPER_PIN);
    servoX.attach(SERVO_X_PIN);
    servoY.attach(SERVO_Y_PIN);

    // 初始化位置
    gripperServo.write(GRIPPER_OPEN);
    servoX.write(posX);
    servoY.write(posY);

    delay(500);
    Serial.println("READY");
}

void loop() {
    // 讀取序列資料
    while (Serial.available() > 0) {
        char c = Serial.read();

        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) {
                processCommand(inputBuffer);
                inputBuffer = "";
            }
        } else {
            inputBuffer += c;
        }
    }
}

void processCommand(String cmd) {
    cmd.trim();

    if (cmd == "G") {
        // 夾取
        gripperClose();
        Serial.println("OK:GRAB");
    }
    else if (cmd == "R") {
        // 釋放
        gripperOpen();
        Serial.println("OK:RELEASE");
    }
    else if (cmd == "L") {
        // 左移
        moveX(-STEP_SIZE);
        Serial.println("OK:LEFT");
    }
    else if (cmd == "H") {
        // 右移
        moveX(STEP_SIZE);
        Serial.println("OK:RIGHT");
    }
    else if (cmd == "U") {
        // 上移
        moveY(-STEP_SIZE);
        Serial.println("OK:UP");
    }
    else if (cmd == "D") {
        // 下移
        moveY(STEP_SIZE);
        Serial.println("OK:DOWN");
    }
    else if (cmd == "C") {
        // 回中心
        posX = 90;
        posY = 90;
        servoX.write(posX);
        servoY.write(posY);
        Serial.println("OK:CENTER");
    }
    else if (cmd.indexOf(',') > 0) {
        // 座標模式: "X,Y"
        int commaIdx = cmd.indexOf(',');
        int targetX = cmd.substring(0, commaIdx).toInt();
        int targetY = cmd.substring(commaIdx + 1).toInt();
        trackTarget(targetX, targetY);
    }
    else {
        Serial.println("ERR:UNKNOWN");
    }
}

void gripperClose() {
    gripperServo.write(GRIPPER_CLOSE);
    gripperClosed = true;
    delay(300);  // 等待夾爪動作完成
}

void gripperOpen() {
    gripperServo.write(GRIPPER_OPEN);
    gripperClosed = false;
    delay(300);
}

void moveX(int delta) {
    posX = constrain(posX + delta, SERVO_X_MIN, SERVO_X_MAX);
    servoX.write(posX);
}

void moveY(int delta) {
    posY = constrain(posY + delta, SERVO_Y_MIN, SERVO_Y_MAX);
    servoY.write(posY);
}

void trackTarget(int targetX, int targetY) {
    /*
     * 根據目標在畫面中的位置，自動調整伺服馬達角度，
     * 使夾爪對準目標。
     *
     * 計算偏差量：
     *   errorX > 0 表示目標在畫面右方 -> 伺服馬達需往右轉
     *   errorY > 0 表示目標在畫面下方 -> 伺服馬達需往下移
     */

    int errorX = targetX - FRAME_CENTER_X;
    int errorY = targetY - FRAME_CENTER_Y;

    // X 軸追蹤
    if (abs(errorX) > DEAD_ZONE) {
        int stepX = (errorX > 0) ? STEP_SIZE : -STEP_SIZE;
        moveX(stepX);
    }

    // Y 軸追蹤
    if (abs(errorY) > DEAD_ZONE) {
        int stepY = (errorY > 0) ? STEP_SIZE : -STEP_SIZE;
        moveY(stepY);
    }

    // 回報目前位置
    Serial.print("POS:");
    Serial.print(posX);
    Serial.print(",");
    Serial.println(posY);
}
