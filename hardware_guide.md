# 🔧 CareBot 하드웨어 조립 가이드 / Hardware Assembly Guide

## 목차 / Table of Contents

1. [필요 부품 목록 / Parts List](#부품-목록)
2. [회로 연결도 / Circuit Diagram](#회로-연결도)
3. [Raspberry Pi GPIO 핀 배치 / GPIO Pin Layout](#gpio-핀-배치)
4. [조립 순서 / Assembly Steps](#조립-순서)
5. [테스트 절차 / Testing Procedure](#테스트-절차)
6. [문제 해결 / Troubleshooting](#문제-해결)

---

## 부품 목록 / Parts List

| 번호 | 부품명 | 규격 | 수량 | 역할 | 예상 가격 |
|------|--------|------|------|------|-----------|
| 1 | Raspberry Pi 4 | 4GB RAM | 1 | 메인 컨트롤러 | ₩65,000 |
| 2 | 리니어 액추에이터 | 12V, 200mm stroke, 최대 150N | 4 | 침대 패널 구동 | ₩40,000/개 |
| 3 | L298N 모터 드라이버 | 듀얼 H-브리지, 2A | 2 | 액추에이터 PWM 제어 | ₩3,000/개 |
| 4 | FSR400 압력 센서 | 0.1~10N 감지 범위 | 4 | 환자 하중 감지 | ₩8,000/개 |
| 5 | ADS1115 ADC | 16비트, I2C | 1 | 아날로그→디지털 변환 | ₩5,000 |
| 6 | 긴급 정지 버튼 | 적색 버섯형, NC 접점 | 1 | 물리적 비상정지 | ₩5,000 |
| 7 | 12V 20A 스위칭 전원 | AC→DC 변환 | 1 | 액추에이터 전원 공급 | ₩30,000 |
| 8 | 5V 3A USB-C 전원 | Raspberry Pi 전용 | 1 | RPi 전원 공급 | ₩15,000 |
| 9 | 40핀 GPIO 케이블 | 점퍼선 포함 | 1 | 배선 연결 | ₩5,000 |
| 10 | 알루미늄 프로파일 20x20 | 침대 프레임 연결용 | 필요량 | 마운팅 구조 | 별도 |
| 11 | LED (녹/황/적) | 5mm | 3 | 상태 표시 | ₩1,000 |
| 12 | 저항 330Ω | 1/4W | 3 | LED 전류 제한 | ₩500 |

**예상 총 비용: 약 ₩340,000 ~ ₩500,000** (프레임 제외)

---

## GPIO 핀 배치 / GPIO Pin Layout

```
Raspberry Pi 4 GPIO 핀맵 (BCM 번호 / BCM Numbering)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

액추에이터 제어 (L298N 연결) / Actuator Control (L298N Connection):
┌────────────────┬──────────────┬───────────────────────────────┐
│ 액추에이터     │ 핀 번호 (BCM) │ 기능                          │
├────────────────┼──────────────┼───────────────────────────────┤
│ 상체 좌 (head_left)  │ 17, 18, 12 │ Extend, Retract, PWM    │
│ 상체 우 (head_right) │ 22, 23, 13 │ Extend, Retract, PWM    │
│ 하체 좌 (foot_left)  │ 24, 25, 18 │ Extend, Retract, PWM    │
│ 하체 우 (foot_right) │ 27, 5, 19  │ Extend, Retract, PWM    │
└────────────────┴──────────────┴───────────────────────────────┘

안전 및 상태 핀 / Safety & Status Pins:
┌─────────────────┬──────────┬──────────────────────────────────┐
│ 장치            │ 핀 (BCM) │ 설명                             │
├─────────────────┼──────────┼──────────────────────────────────┤
│ 긴급 정지 버튼  │ 26       │ 풀업 저항, FALLING 엣지 감지     │
│ LED 녹색 (정상) │ 6        │ 정상 운영 중                     │
│ LED 황색 (변환) │ 13       │ 자세 변환 중                     │
│ LED 적색 (오류) │ 19       │ 오류 / 긴급 정지 상태            │
└─────────────────┴──────────┴──────────────────────────────────┘

I2C 통신 (ADS1115) / I2C Communication (ADS1115):
- SDA: GPIO 2 (핀 3)
- SCL: GPIO 3 (핀 5)
- VCC: 3.3V (핀 1)
- GND: GND (핀 6)
```

---

## 회로 연결도 / Circuit Diagram

```
12V 전원 공급기             Raspberry Pi 4
━━━━━━━━━━━━━━━━           ━━━━━━━━━━━━━━
+12V ──────────────────→ L298N VCC (×2)
GND ───────────────────→ 공통 GND

L298N #1 (상체 좌/우 / Head Left/Right):
  IN1, IN2 ←── GPIO 17, 18 (head_left extend/retract)
  IN3, IN4 ←── GPIO 22, 23 (head_right extend/retract)
  ENA      ←── GPIO 12 (head_left PWM)
  ENB      ←── GPIO 13 (head_right PWM)
  OUT1,2   ───→ 리니어 액추에이터 #1 (상체 좌)
  OUT3,4   ───→ 리니어 액추에이터 #2 (상체 우)

L298N #2 (하체 좌/우 / Foot Left/Right):
  IN1, IN2 ←── GPIO 24, 25 (foot_left extend/retract)
  IN3, IN4 ←── GPIO 27, 5  (foot_right extend/retract)
  ENA      ←── GPIO 18 (foot_left PWM)
  ENB      ←── GPIO 19 (foot_right PWM)
  OUT1,2   ───→ 리니어 액추에이터 #3 (하체 좌)
  OUT3,4   ───→ 리니어 액추에이터 #4 (하체 우)

ADS1115 (압력 센서 ADC):
  A0, A1, A2, A3 ←── FSR400 압력 센서 ×4 (각 10kΩ 풀다운 저항)
  SDA, SCL ──────→ GPIO 2, 3 (I2C)

긴급 정지 버튼:
  핀1 (NC) ──→ GPIO 26
  핀2      ──→ GND
  (내부 풀업 저항 사용 / Uses internal pull-up)
```

---

## 조립 순서 / Assembly Steps

### 1단계: 전원 시스템 구성 / Step 1: Power System Setup

```bash
⚠️ 반드시 전원을 끈 상태에서 작업하세요!
⚠️ Always work with power OFF!

1. 12V 전원 공급기를 침대 프레임 하부에 고정
2. 12V 라인을 각 L298N 모터 드라이버의 VCC에 연결
3. 공통 GND 연결 (12V GND = Raspberry Pi GND = 공통)
4. 5V USB-C 전원을 Raspberry Pi에 연결 (별도 전원 사용 권장)
```

### 2단계: 모터 드라이버 연결 / Step 2: Motor Driver Connection

```bash
1. L298N #1을 상체 패널 근처에 고정
2. L298N #2를 하체 패널 근처에 고정
3. GPIO 점퍼선으로 Raspberry Pi → L298N 연결 (핀 배치 참조)
4. 리니어 액추에이터 출력선을 OUT 단자에 연결
   - 극성 주의: 연결 후 테스트로 방향 확인
```

### 3단계: 압력 센서 연결 / Step 3: Pressure Sensor Connection

```bash
1. ADS1115를 Raspberry Pi I2C에 연결
   SDA → GPIO2, SCL → GPIO3, VCC → 3.3V, GND → GND
2. FSR400 센서 4개를 환자 누울 위치 (상체 2개, 하체 2개)에 배치
3. 각 FSR400을 10kΩ 풀다운 저항과 직렬 연결
4. ADS1115 A0~A3에 각 센서 연결
```

### 4단계: 안전 장치 / Step 4: Safety Devices

```bash
1. 긴급 정지 버튼을 환자 손 닿는 위치에 고정
2. GPIO26 → 버튼 → GND 연결
3. LED 3개 (녹/황/적)를 330Ω 저항과 함께 각 GPIO에 연결
4. 버튼 동작 테스트: 누르면 GPIO26 LOW → 즉시 정지
```

---

## 테스트 절차 / Testing Procedure

```bash
# 1. 시뮬레이션 모드 먼저 테스트 / Test simulation mode first
SIMULATION_MODE=true python carebot_core/main.py

# 2. 실제 하드웨어 GPIO 테스트 (Raspberry Pi에서)
# Test actual hardware GPIO (on Raspberry Pi)
python tests/test_gpio_basic.py

# 3. 액추에이터 방향 확인 (각 하나씩)
# Verify actuator direction (one at a time)
python tests/test_actuator_single.py --actuator head_left --direction extend --seconds 2

# 4. 압력 센서 값 확인
# Check pressure sensor values
python tests/test_pressure_sensors.py

# 5. 긴급 정지 버튼 테스트
# Test emergency stop button
python tests/test_emergency_stop.py

# 6. 전체 자세 변환 테스트 (속도: 빠름)
# Full position change test (speed: fast)
python tests/test_full_rotation.py
```

---

## 문제 해결 / Troubleshooting

| 증상 | 원인 | 해결방법 |
|------|------|---------|
| 액추에이터가 반대로 움직임 | 극성 반전 | 모터 드라이버 OUT 단자 배선 교체 |
| 압력 센서 값이 0 | I2C 연결 불량 | SDA/SCL 연결 확인, `i2cdetect -y 1` |
| 긴급 정지 버튼 무반응 | GPIO26 미연결 | 배선 확인, 풀업 저항 설정 확인 |
| 액추에이터 약하게 움직임 | 전원 전압 부족 | 12V 전원 공급기 전류 용량 확인 (20A 이상) |
| RPi 재부팅 반복 | 전원 부족 | 5V 3A 이상 전원 사용, 별도 전원 권장 |

---

## ⚠️ 안전 주의사항 / Safety Warnings

> **반드시 숙지하세요 / Must read before assembly**

1. **의료 기기 아님 / Not a medical device** — 반드시 의료진 감독 하에 사용
2. **최초 가동 시** — 환자 없이 빈 침대에서 먼저 테스트
3. **긴급 정지 버튼** — 항상 환자 손 닿는 위치에 배치
4. **이동 속도** — `MOVEMENT_STEPS`를 늘릴수록 더 천천히 이동 (권장: 30 이상)
5. **전기 안전** — 12V 배선은 반드시 퓨즈 사용 (5A 퓨즈 권장)
6. **야간 운영** — 첫 주는 보호자 상주 상태에서 운영 테스트
