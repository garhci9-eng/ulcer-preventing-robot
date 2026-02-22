"""
CareBot Core — 욕창 방지 자세 변환 로봇 메인 제어 모듈
CareBot Core — Main control module for pressure ulcer prevention robot

작성자 / Author: CareBot OSS Team
라이선스 / License: GPL-3.0
공익 목적 / Public Benefit Purpose Only
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime
from enum import Enum

# 시뮬레이션 모드 여부 확인 (하드웨어 없을 때 테스트용)
# Check simulation mode (for testing without hardware)
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

if not SIMULATION_MODE:
    try:
        import RPi.GPIO as GPIO
    except ImportError:
        print("⚠️  RPi.GPIO를 불러올 수 없습니다. SIMULATION_MODE=true 로 실행하세요.")
        print("⚠️  RPi.GPIO not available. Run with SIMULATION_MODE=true")
        sys.exit(1)

# 로깅 설정 / Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/carebot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("carebot.core")


# ─────────────────────────────────────────────
# 자세 정의 / Patient Position Definitions
# ─────────────────────────────────────────────
class Position(str, Enum):
    SUPINE = "supine"           # 앙와위 (등 대고 누운 자세)
    LEFT_LATERAL = "left_lateral"   # 좌측와위 (왼쪽으로 기울임)
    RIGHT_LATERAL = "right_lateral" # 우측와위 (오른쪽으로 기울임)


# 자세 순환 순서 (권장: 앙와위 → 좌측 → 앙와위 → 우측)
# Recommended rotation: supine → left → supine → right
POSITION_ROTATION = [
    Position.SUPINE,
    Position.LEFT_LATERAL,
    Position.SUPINE,
    Position.RIGHT_LATERAL,
]

# 각 자세의 액추에이터 목표값 (0~100%)
# Actuator target values for each position (0~100%)
POSITION_TARGETS = {
    Position.SUPINE: {
        "head_left": 0,    # 좌측 상체 패널
        "head_right": 0,   # 우측 상체 패널
        "foot_left": 0,    # 좌측 하체 패널
        "foot_right": 0,   # 우측 하체 패널
    },
    Position.LEFT_LATERAL: {
        "head_left": 60,   # 좌측으로 30도 기울기
        "head_right": 10,
        "foot_left": 60,
        "foot_right": 10,
    },
    Position.RIGHT_LATERAL: {
        "head_left": 10,   # 우측으로 30도 기울기
        "head_right": 60,
        "foot_left": 10,
        "foot_right": 60,
    },
}

# 한국어 자세 이름 (로그 및 UI 표시용)
# Korean position names for logs and UI
POSITION_NAMES_KO = {
    Position.SUPINE: "앙와위 (등 대고 누운 자세)",
    Position.LEFT_LATERAL: "좌측와위 (왼쪽 기울임 30°)",
    Position.RIGHT_LATERAL: "우측와위 (오른쪽 기울임 30°)",
}


# ─────────────────────────────────────────────
# GPIO 핀 설정 / GPIO Pin Configuration
# ─────────────────────────────────────────────
class PinConfig:
    # 액추에이터 제어 핀 (L298N 드라이버 연결)
    # Actuator control pins (connected to L298N driver)
    ACTUATORS = {
        "head_left":  {"extend": 17, "retract": 18, "pwm": 12},
        "head_right": {"extend": 22, "retract": 23, "pwm": 13},
        "foot_left":  {"extend": 24, "retract": 25, "pwm": 18},
        "foot_right": {"extend": 27, "retract": 5,  "pwm": 19},
    }

    # 압력 센서 핀 (ADS1115 ADC via I2C)
    # Pressure sensor pins (ADS1115 ADC via I2C)
    PRESSURE_SENSOR_I2C_ADDRESS = 0x48

    # 긴급 정지 버튼 핀 (풀업 저항 사용)
    # Emergency stop button pin (pull-up resistor)
    EMERGENCY_STOP_PIN = 26

    # 상태 LED 핀
    # Status LED pins
    LED_GREEN = 6   # 정상 동작 중
    LED_YELLOW = 13 # 자세 변환 중
    LED_RED = 19    # 오류 / 긴급 정지


# ─────────────────────────────────────────────
# 액추에이터 컨트롤러 / Actuator Controller
# ─────────────────────────────────────────────
class ActuatorController:
    """
    리니어 액추에이터 제어 클래스
    Controls linear actuators via GPIO PWM signals
    """

    def __init__(self, simulation: bool = False):
        self.simulation = simulation
        self.current_positions = {k: 0 for k in PinConfig.ACTUATORS}
        self.pwm_objects = {}

        if not simulation:
            self._setup_gpio()
        else:
            logger.info("🔧 시뮬레이션 모드로 액추에이터 초기화 / Actuator initialized in simulation mode")

    def _setup_gpio(self):
        """GPIO 핀 초기화 / Initialize GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for name, pins in PinConfig.ACTUATORS.items():
            GPIO.setup(pins["extend"], GPIO.OUT)
            GPIO.setup(pins["retract"], GPIO.OUT)
            GPIO.setup(pins["pwm"], GPIO.OUT)

            # PWM 주파수 100Hz로 설정
            # Set PWM frequency to 100Hz
            pwm = GPIO.PWM(pins["pwm"], 100)
            pwm.start(0)
            self.pwm_objects[name] = pwm

        # 긴급 정지 버튼 입력 설정
        # Setup emergency stop button input
        GPIO.setup(PinConfig.EMERGENCY_STOP_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(
            PinConfig.EMERGENCY_STOP_PIN,
            GPIO.FALLING,
            callback=self._emergency_stop_callback,
            bouncetime=300,
        )

        logger.info("✅ GPIO 초기화 완료 / GPIO initialization complete")

    def _emergency_stop_callback(self, channel):
        """긴급 정지 버튼 콜백 / Emergency stop button callback"""
        logger.critical("🚨 긴급 정지 버튼 눌림! 모든 액추에이터 즉시 정지!")
        logger.critical("🚨 EMERGENCY STOP PRESSED! All actuators halted immediately!")
        self.emergency_stop()

    def emergency_stop(self):
        """모든 액추에이터 즉시 정지 / Halt all actuators immediately"""
        if not self.simulation:
            for name, pins in PinConfig.ACTUATORS.items():
                GPIO.output(pins["extend"], GPIO.LOW)
                GPIO.output(pins["retract"], GPIO.LOW)
                if name in self.pwm_objects:
                    self.pwm_objects[name].ChangeDutyCycle(0)
        logger.critical("⛔ 긴급 정지 완료 / Emergency stop completed")

    async def move_to_position(
        self,
        target_name: str,
        target_values: dict,
        steps: int = 30,
        step_delay: float = 0.3,
    ):
        """
        목표 자세로 점진적 이동 (급격한 움직임 방지)
        Gradually move to target position (prevents sudden movements)

        Args:
            target_name: 자세 이름 / Position name
            target_values: 각 액추에이터 목표값 (0~100) / Target values per actuator
            steps: 이동 단계 수 / Number of movement steps
            step_delay: 단계 간 대기 시간(초) / Delay between steps (seconds)
        """
        logger.info(f"🔄 자세 변환 시작: {target_name} / Position change starting: {target_name}")

        for step in range(1, steps + 1):
            ratio = step / steps  # 0.0 → 1.0 선형 보간

            for actuator_name, target_pct in target_values.items():
                current = self.current_positions[actuator_name]
                new_pct = current + (target_pct - current) * ratio

                if not self.simulation:
                    self._set_actuator(actuator_name, new_pct)
                else:
                    # 시뮬레이션: 값만 업데이트
                    self.current_positions[actuator_name] = new_pct

            await asyncio.sleep(step_delay)

        # 목표 위치로 최종 설정
        # Final set to target position
        for actuator_name, target_pct in target_values.items():
            self.current_positions[actuator_name] = target_pct
            if not self.simulation:
                self._set_actuator(actuator_name, target_pct)

        logger.info(f"✅ 자세 변환 완료: {target_name} / Position change complete: {target_name}")

    def _set_actuator(self, name: str, percent: float):
        """
        특정 액추에이터를 지정된 퍼센트 위치로 설정
        Set specific actuator to given percent position
        """
        pins = PinConfig.ACTUATORS[name]
        current = self.current_positions.get(name, 0)

        if percent > current:
            # 확장 (extend)
            GPIO.output(pins["extend"], GPIO.HIGH)
            GPIO.output(pins["retract"], GPIO.LOW)
        elif percent < current:
            # 수축 (retract)
            GPIO.output(pins["extend"], GPIO.LOW)
            GPIO.output(pins["retract"], GPIO.HIGH)
        else:
            # 정지
            GPIO.output(pins["extend"], GPIO.LOW)
            GPIO.output(pins["retract"], GPIO.LOW)

        # PWM duty cycle 설정 (속도 제어)
        duty = min(max(abs(percent - current), 20), 80)  # 20~80% 범위
        self.pwm_objects[name].ChangeDutyCycle(duty)
        self.current_positions[name] = percent

    def cleanup(self):
        """GPIO 정리 / GPIO cleanup"""
        if not self.simulation:
            self.emergency_stop()
            for pwm in self.pwm_objects.values():
                pwm.stop()
            GPIO.cleanup()
        logger.info("🧹 GPIO 정리 완료 / GPIO cleanup complete")


# ─────────────────────────────────────────────
# 안전 검사 모듈 / Safety Check Module
# ─────────────────────────────────────────────
class SafetyChecker:
    """
    자세 변환 전 안전 상태를 확인하는 클래스
    Safety verification before any position change
    """

    def __init__(self, simulation: bool = False):
        self.simulation = simulation
        self.min_pressure_threshold = 500  # 최소 압력 (환자 감지)
        self.max_pressure_threshold = 5000 # 최대 압력 (과부하)

    async def is_safe_to_move(self) -> tuple[bool, str]:
        """
        이동 가능 여부 종합 판단
        Comprehensive safety check before movement

        Returns:
            (safe: bool, reason: str)
        """
        checks = [
            await self._check_patient_presence(),
            await self._check_no_obstruction(),
            await self._check_actuator_health(),
        ]

        failed = [reason for ok, reason in checks if not ok]
        if failed:
            return False, " | ".join(failed)

        return True, "모든 안전 검사 통과 / All safety checks passed"

    async def _check_patient_presence(self) -> tuple[bool, str]:
        """환자 감지 확인 / Check patient presence"""
        if self.simulation:
            return True, "OK"

        # ADS1115에서 압력 센서 값 읽기
        # Read pressure sensor values from ADS1115
        try:
            import smbus2
            bus = smbus2.SMBus(1)
            # 실제 I2C 구현은 하드웨어에 맞게 수정 필요
            # Actual I2C implementation needs to match hardware
            pressure_value = 1000  # placeholder
            bus.close()

            if pressure_value < self.min_pressure_threshold:
                return False, "⚠️ 환자 미감지 — 침대 위 환자 없음 / Patient not detected"
            return True, "OK"
        except Exception as e:
            logger.warning(f"압력 센서 읽기 실패 / Pressure sensor read failed: {e}")
            return True, "OK"  # 센서 오류 시 진행 허용 (보수적 선택)

    async def _check_no_obstruction(self) -> tuple[bool, str]:
        """장애물 확인 / Check for obstructions"""
        # TODO: 초음파 센서 또는 카메라 기반 장애물 감지 추가
        # TODO: Add ultrasonic sensor or camera-based obstruction detection
        return True, "OK"

    async def _check_actuator_health(self) -> tuple[bool, str]:
        """액추에이터 상태 확인 / Check actuator health"""
        if self.simulation:
            return True, "OK"
        # TODO: 전류 센서 기반 과부하 감지 추가
        # TODO: Add current sensor-based overload detection
        return True, "OK"


# ─────────────────────────────────────────────
# 자세 변환 스케줄러 / Position Rotation Scheduler
# ─────────────────────────────────────────────
class PositionScheduler:
    """
    90분마다 환자 자세를 자동 변환하는 스케줄러
    Scheduler that automatically repositions patient every 90 minutes

    의학적 권고사항: 욕창 예방을 위해 2시간마다 자세 변환 권장
    Medical guideline: Reposition every 2 hours for pressure ulcer prevention
    (본 시스템은 1.5시간으로 더 자주 변환 / This system uses 1.5hr for extra safety)
    """

    # 자세 변환 주기 (초 단위 / in seconds)
    ROTATION_INTERVAL_SECONDS = 90 * 60  # 90분 = 5400초

    def __init__(
        self,
        actuator: ActuatorController,
        safety: SafetyChecker,
        alert_callback=None,
    ):
        self.actuator = actuator
        self.safety = safety
        self.alert_callback = alert_callback  # 보호자 알림 콜백 / Caregiver alert callback

        self.rotation_index = 0
        self.is_running = False
        self.is_paused = False
        self.last_rotation_time: datetime | None = None
        self.next_rotation_time: datetime | None = None
        self.total_rotations = 0

        # 현재 자세 / Current position
        self.current_position = Position.SUPINE

    async def start(self):
        """스케줄러 시작 / Start scheduler"""
        self.is_running = True
        logger.info(f"🚀 CareBot 스케줄러 시작 / Scheduler started")
        logger.info(f"⏱️  자세 변환 주기: {self.ROTATION_INTERVAL_SECONDS // 60}분 마다")
        logger.info(f"⏱️  Rotation interval: every {self.ROTATION_INTERVAL_SECONDS // 60} minutes")

        # 초기 자세: 앙와위로 설정
        # Initial position: supine
        await self._apply_position(Position.SUPINE)

        while self.is_running:
            # 다음 자세 변환 시각 계산
            # Calculate next rotation time
            import time
            self.next_rotation_time = datetime.now()
            await asyncio.sleep(self.ROTATION_INTERVAL_SECONDS)

            if not self.is_running:
                break

            if self.is_paused:
                logger.info("⏸️  스케줄러 일시정지 중 / Scheduler paused — skipping rotation")
                continue

            await self._perform_rotation()

    async def _perform_rotation(self):
        """자세 변환 수행 / Perform position rotation"""
        # 다음 자세 결정
        # Determine next position
        self.rotation_index = (self.rotation_index + 1) % len(POSITION_ROTATION)
        next_position = POSITION_ROTATION[self.rotation_index]

        logger.info(f"⏰ 자세 변환 시각 도래 / Rotation time reached")
        logger.info(f"   현재: {POSITION_NAMES_KO[self.current_position]}")
        logger.info(f"   목표: {POSITION_NAMES_KO[next_position]}")

        # 안전 검사
        # Safety check
        is_safe, reason = await self.safety.is_safe_to_move()
        if not is_safe:
            logger.warning(f"⚠️  안전 검사 실패 — 자세 변환 취소 / Safety check failed: {reason}")
            if self.alert_callback:
                await self.alert_callback(
                    level="warning",
                    message=f"자세 변환 취소됨: {reason}",
                    requires_manual=True,
                )
            return

        # 자세 변환 실행
        # Execute position change
        try:
            await self._apply_position(next_position)
            self.total_rotations += 1
            self.last_rotation_time = datetime.now()

            # 보호자 알림 (정상 완료)
            # Caregiver alert (normal completion)
            if self.alert_callback:
                await self.alert_callback(
                    level="info",
                    message=f"자세 변환 완료: {POSITION_NAMES_KO[next_position]}",
                    requires_manual=False,
                )

        except Exception as e:
            logger.error(f"❌ 자세 변환 오류 / Position change error: {e}")
            self.actuator.emergency_stop()
            if self.alert_callback:
                await self.alert_callback(
                    level="critical",
                    message=f"자세 변환 오류 발생! 즉시 확인 필요: {str(e)}",
                    requires_manual=True,
                )

    async def _apply_position(self, position: Position):
        """특정 자세 적용 / Apply specific position"""
        target = POSITION_TARGETS[position]
        await self.actuator.move_to_position(
            target_name=POSITION_NAMES_KO[position],
            target_values=target,
        )
        self.current_position = position

    def pause(self):
        """자동 스케줄 일시정지 / Pause automatic schedule"""
        self.is_paused = True
        logger.info("⏸️  자동 자세 변환 일시정지 / Automatic rotation paused")

    def resume(self):
        """자동 스케줄 재개 / Resume automatic schedule"""
        self.is_paused = False
        logger.info("▶️  자동 자세 변환 재개 / Automatic rotation resumed")

    def stop(self):
        """스케줄러 종료 / Stop scheduler"""
        self.is_running = False
        logger.info("🛑 스케줄러 종료 / Scheduler stopped")

    def get_status(self) -> dict:
        """현재 상태 반환 / Return current status"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "current_position": self.current_position.value,
            "current_position_ko": POSITION_NAMES_KO[self.current_position],
            "last_rotation_time": (
                self.last_rotation_time.isoformat()
                if self.last_rotation_time
                else None
            ),
            "next_rotation_time": (
                self.next_rotation_time.isoformat()
                if self.next_rotation_time
                else None
            ),
            "total_rotations": self.total_rotations,
            "rotation_interval_minutes": self.ROTATION_INTERVAL_SECONDS // 60,
        }


# ─────────────────────────────────────────────
# 메인 진입점 / Main Entry Point
# ─────────────────────────────────────────────
async def main():
    """CareBot 메인 실행 함수 / CareBot main execution function"""

    logger.info("=" * 60)
    logger.info("🏥 CareBot — 욕창 방지 자세 변환 로봇 시스템 시작")
    logger.info("🏥 CareBot — Pressure Ulcer Prevention Robot Starting")
    logger.info(f"   모드 / Mode: {'시뮬레이션' if SIMULATION_MODE else '실제 하드웨어'}")
    logger.info("=" * 60)

    # 컴포넌트 초기화
    # Initialize components
    actuator = ActuatorController(simulation=SIMULATION_MODE)
    safety = SafetyChecker(simulation=SIMULATION_MODE)

    async def caregiver_alert(level: str, message: str, requires_manual: bool):
        """보호자 알림 처리 / Caregiver alert handler"""
        logger.info(f"📢 보호자 알림 [{level.upper()}]: {message}")
        if requires_manual:
            logger.warning("👤 수동 확인이 필요합니다! / Manual check required!")
        # TODO: SMS, 카카오톡, 앱 푸시 알림 연동
        # TODO: Integrate SMS, KakaoTalk, app push notifications

    scheduler = PositionScheduler(
        actuator=actuator,
        safety=safety,
        alert_callback=caregiver_alert,
    )

    # 종료 시그널 처리 / Handle shutdown signals
    def shutdown_handler(sig, frame):
        logger.info("\n⚠️  종료 신호 수신 / Shutdown signal received")
        scheduler.stop()
        actuator.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # 스케줄러 실행 (비동기 루프)
    # Run scheduler (async loop)
    try:
        await scheduler.start()
    except Exception as e:
        logger.critical(f"💥 치명적 오류 / Critical error: {e}")
        actuator.emergency_stop()
        actuator.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
