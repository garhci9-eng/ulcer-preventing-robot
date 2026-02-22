[README (4).md](https://github.com/user-attachments/files/25465398/README.4.md)
# 🏥 CareBot
### 욕창 방지 자세 변환 로봇 플랫폼 / Pressure Ulcer Prevention Auto-Repositioning Robot Platform

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](/)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB)](/)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D)](/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](./LICENSE)
[![Purpose](https://img.shields.io/badge/목적-공익%20전용-green)](/)
[![Idea](https://img.shields.io/badge/아이디어-사람%2050%25%20%2B%20Claude%2050%25-blueviolet)](/)

---

## 👥 프로젝트 기여 / Project Credits

> 이 프로젝트는 **사람의 아이디어**와 **Claude AI의 구현**이 동등하게 결합된 협업 결과물입니다.  
> This project is a collaboration where **human ideas** and **Claude AI's implementation** contributed equally.

| 역할 / Role | 기여자 / Contributor | 기여도 / Contribution |
|-------------|----------------------|-----------------------|
| 💡 아이디어 & 도메인 지식 (Idea & Domain Knowledge) | 사람 (Human) | **50%** |
| 🤖 코드 구현 & 아키텍처 (Code & Architecture) | Claude AI (Anthropic) | **50%** |

**아이디어 — 사람 (Human) 50%:**
- 욕창 방지를 위한 자동 자세 변환 필요성 발견
- 거동 불능 환자를 대상으로 한 로봇 간병 개념 정의
- 90분 주기 자세 변환이라는 의학적 요구사항 제시
- 공익 목적 오픈소스로 배포한다는 방향 결정
- Identifying the need for automated repositioning to prevent pressure ulcers
- Defining the target use case: immobile patients in care settings
- Specifying the 90-minute medical repositioning requirement
- Deciding to release as open-source for public benefit only

**구현 — Claude AI (Anthropic) 50%:**
- Python 비동기 제어 시스템 (asyncio, Raspberry Pi GPIO)
- FastAPI REST API + WebSocket 실시간 서버
- Vue 3 모니터링 대시보드 설계 및 구현
- 안전 시스템 아키텍처 (긴급 정지, 점진적 이동, 압력 감지)
- 프로젝트 전체 구조 및 문서화
- Python async control system (asyncio, Raspberry Pi GPIO)
- FastAPI REST API + WebSocket real-time server
- Vue 3 monitoring dashboard design and implementation
- Safety system architecture (emergency stop, gradual movement, pressure detection)
- Overall project structure and documentation

---

## 🎯 문제 정의 / The Problem

**한국어:**  
거동이 불편한 환자는 장시간 같은 자세를 유지할 경우 **욕창(압박 궤양)** 이 발생합니다. 의료 지침에 따르면 2시간마다 자세를 변환해야 하지만, 간호 인력 부족으로 이를 지키지 못하는 경우가 많습니다. 특히 야간에 이 문제가 심각합니다.

**English:**  
Immobile patients develop **pressure ulcers** when kept in the same position for too long. Medical guidelines recommend repositioning every 2 hours, but understaffed care facilities often cannot maintain this schedule — especially overnight.

> *"압박 궤양의 93%는 예방 가능하다"* — 한국간호학회 (2022)  
> *"93% of pressure ulcers are preventable"* — Korean Nursing Association (2022)

---

## 💡 솔루션 / The Solution

**CareBot**은 침대에 장착된 리니어 액추에이터를 통해 **90분마다 자동으로 환자 자세를 변환**합니다.  
**CareBot** uses linear actuators mounted to the bed to **automatically reposition patients every 90 minutes**.

자세 순환 / Position Rotation:
```
앙와위 (Supine)
  → 좌측와위 (Left Lateral 30°)
    → 앙와위 (Supine)
      → 우측와위 (Right Lateral 30°)
        → 반복 (Repeat)
```

---

## ✨ 주요 기능 / Key Features

| 기능 / Feature | 설명 / Description |
|---|---|
| ⏱️ **자동 자세 변환** / Auto Repositioning | 90분마다 앙와위 ↔ 측와위 자동 순환 / Rotates supine ↔ lateral every 90 min |
| 🦾 **액추에이터 제어** / Actuator Control | Raspberry Pi GPIO → L298N → 리니어 액추에이터 / GPIO PWM control |
| 🛡️ **다중 안전 시스템** / Multi-layer Safety | 긴급 정지, 압력 감지, 점진적 이동 / Emergency stop, pressure detection, gradual movement |
| 📊 **실시간 대시보드** / Real-time Dashboard | Vue 3 + WebSocket 실시간 상태 모니터링 / Live status monitoring |
| 🤖 **AI 상태 분석** / AI Analysis | Claude API 기반 보호자 안내 요약 / Caregiver summaries powered by Claude |
| 📱 **보호자 알림** / Caregiver Alerts | 변환 완료 및 이상 감지 시 즉시 알림 / Instant alerts on completion or anomaly |

---

## 🏗️ 시스템 구조 / System Architecture

```
CareBot System
│
├── 🔧 carebot_core/          # 로봇 제어 / Robot Control (Python + asyncio)
│   └── main.py               # GPIO 제어, 90분 스케줄러, 안전 시스템
│                             # GPIO control, 90-min scheduler, safety system
│
├── 🌐 carebot_api/           # 백엔드 서버 / Backend Server (FastAPI)
│   ├── main.py               # REST API + WebSocket 엔드포인트
│   └── services/
│       └── ai_service.py     # Claude API 연동 / Claude API integration
│
├── 🖥️  carebot_dashboard/    # 프론트엔드 / Frontend (Vue 3 + Tailwind)
│   └── src/App.vue           # 실시간 모니터링 UI / Real-time monitoring UI
│
├── 🧪 tests/                 # 단위 테스트 / Unit Tests (pytest)
├── 📖 docs/                  # 조립 가이드, 회로도 / Assembly guide, circuit diagram
├── .env.example              # 환경변수 예시 / Environment variable template
└── requirements.txt          # Python 의존성 / Python dependencies
```

---

## 🔧 하드웨어 요구사항 / Hardware Requirements

| 부품 / Part | 수량 / Qty | 역할 / Role | 예상 가격 / Est. Cost |
|---|---|---|---|
| Raspberry Pi 4 (4GB) | 1 | 메인 컨트롤러 / Main controller | ₩65,000 |
| 12V 리니어 액추에이터 (200mm) | 4 | 침대 패널 구동 / Bed panel actuation | ₩40,000 × 4 |
| L298N 모터 드라이버 | 2 | PWM 제어 / PWM control | ₩3,000 × 2 |
| FSR400 압력 센서 | 4 | 환자 감지 / Patient detection | ₩8,000 × 4 |
| ADS1115 ADC (I2C) | 1 | 아날로그→디지털 / Analog→Digital | ₩5,000 |
| 긴급 정지 버튼 (적색) | 1 | 비상 정지 / Emergency stop | ₩5,000 |
| 12V 20A 전원 공급기 | 1 | 액추에이터 전원 / Actuator power | ₩30,000 |

**예상 총 비용 / Estimated Total: ₩340,000 ~ ₩500,000** (프레임 제외 / excluding frame)

자세한 조립 가이드 → [`docs/hardware_guide.md`](./docs/hardware_guide.md)

---

## ⚡ 빠른 시작 / Quick Start

### 1. 설치 / Installation
```bash
git clone https://github.com/YOUR_ID/carebot.git
cd carebot

# Python 가상환경 / Python virtual environment
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 환경 설정 / Environment setup
cp .env.example .env
# .env 파일에서 ANTHROPIC_API_KEY 입력 / Set ANTHROPIC_API_KEY in .env
```

### 2. 시뮬레이션 모드 (하드웨어 없이 테스트) / Simulation Mode (Test without hardware)
```bash
# 터미널 1 — 로봇 제어 / Terminal 1 — Robot control
SIMULATION_MODE=true python carebot_core/main.py

# 터미널 2 — API 서버 / Terminal 2 — API server
uvicorn carebot_api.main:app --host 0.0.0.0 --port 8000 --reload

# 터미널 3 — 대시보드 / Terminal 3 — Dashboard
cd carebot_dashboard && npm install && npm run dev
# → http://localhost:5173
```

### 3. 테스트 / Run Tests
```bash
SIMULATION_MODE=true pytest tests/ -v
```

---

## 📡 API 엔드포인트 / API Endpoints

| Method | Endpoint | 설명 / Description |
|--------|----------|--------------------|
| `GET` | `/api/status` | 현재 자세 & 상태 / Current position & status |
| `POST` | `/api/position/rotate` | 수동 자세 변환 / Manual rotation |
| `POST` | `/api/emergency-stop` | 🚨 긴급 정지 / Emergency stop |
| `POST` | `/api/scheduler/pause` | 스케줄 일시정지 / Pause schedule |
| `POST` | `/api/scheduler/resume` | 스케줄 재개 / Resume schedule |
| `GET` | `/api/logs` | 자세 변환 기록 / Change history |
| `GET` | `/api/ai/summary` | AI 상태 요약 / AI status summary |
| `WS` | `/ws` | 실시간 WebSocket / Real-time WebSocket |

---

## 🛡️ 안전 시스템 / Safety System

- **🔴 물리적 긴급 정지 버튼** / Physical Emergency Stop — 누르면 모든 액추에이터 즉시 정지 / Instantly halts all actuators
- **📈 점진적 이동** / Gradual Movement — 30단계 천천히 변환, 급격한 움직임 없음 / 30-step gradual transition
- **⚖️ 압력 센서 확인** / Pressure Verification — 이동 전 환자 감지 필수 / Verifies patient presence before movement
- **⚡ 과부하 감지** / Overload Detection — 비정상 전류 감지 시 자동 정지 / Auto-stop on abnormal current
- **📢 보호자 즉시 알림** / Instant Alerts — 이상 시 SMS/앱 알림 / SMS/app alert on anomaly
- **📝 전체 감사 로그** / Full Audit Log — 시각, 자세, 결과 전부 기록 / All actions logged with timestamp

---

## ⚠️ 중요 공지 / Important Notice

> **이 소프트웨어는 공익 목적으로만 사용되어야 합니다.**  
> **This software must be used for public benefit purposes only.**
>
> **이 소프트웨어는 의료기기가 아닙니다.**  
> **This software is NOT a certified medical device.**

- 실제 환자에게 사용하기 전 반드시 의료 전문가의 감독 하에 검증하십시오  
  Always validate under medical supervision before use on real patients
- 이 시스템은 간호 인력을 **보조**하는 도구이며, 완전히 **대체**할 수 없습니다  
  This system **supplements** nursing care — it cannot fully **replace** it

---

## 📖 문서 / Documentation

| 문서 / Document | 설명 / Description |
|---|---|
| [`docs/hardware_guide.md`](./docs/hardware_guide.md) | 하드웨어 조립 가이드 & 회로도 / Assembly guide & circuit diagram |
| [`docs/safety_protocol.md`](./docs/safety_protocol.md) | 안전 프로토콜 / Safety protocol |
| [`docs/api.md`](./docs/api.md) | API 전체 명세 / Full API specification |
| [`docs/medical_disclaimer.md`](./docs/medical_disclaimer.md) | 의료 면책 고지 / Medical disclaimer |

---

## 🤝 기여하기 / Contributing

이 프로젝트는 공익을 위한 오픈소스입니다.  
의료진, 개발자, 간병인, 복지 연구자 모두 환영합니다!  
This is an open-source project for public benefit.  
Medical professionals, developers, caregivers, and welfare researchers are all welcome!

```bash
git checkout -b feat/기능이름
git commit -m "feat: 설명 / description"
# Pull Request 제출 / Submit Pull Request
```

---

## 📜 라이선스 / License

**GPL-3.0** — 소스 공개 강제, 공익적 활용 장려  
**GPL-3.0** — Requires source disclosure, encourages public benefit use  
상업적 이용 시 별도 문의 / Contact for commercial use

---

## 🙏 감사의 말 / Acknowledgments

이 프로젝트를 가능하게 해준 모든 간병인과 의료 종사자분들께 감사드립니다.  
욕창으로 고통받는 모든 환자분들을 위해 이 프로젝트를 바칩니다.

Dedicated to all caregivers working tirelessly to prevent pressure ulcers,  
and to every patient who deserves dignity and comfort in their care.
