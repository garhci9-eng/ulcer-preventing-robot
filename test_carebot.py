"""
CareBot 단위 테스트 / Unit Tests
시뮬레이션 모드에서 핵심 로직 검증 / Core logic validation in simulation mode
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# 시뮬레이션 모드 강제 설정 / Force simulation mode for testing
os.environ["SIMULATION_MODE"] = "true"

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from carebot_core.main import (
    ActuatorController,
    Position,
    POSITION_ROTATION,
    POSITION_TARGETS,
    POSITION_NAMES_KO,
    PositionScheduler,
    SafetyChecker,
)


# ─────────────────────────────────────────────
# 액추에이터 테스트 / Actuator Tests
# ─────────────────────────────────────────────
class TestActuatorController:

    def test_초기화_시_모든_액추에이터_0위치(self):
        """모든 액추에이터가 0%에서 시작되어야 함 / All actuators should start at 0%"""
        actuator = ActuatorController(simulation=True)
        for name, pos in actuator.current_positions.items():
            assert pos == 0, f"{name} 초기값이 0이 아님 / {name} initial value is not 0"

    @pytest.mark.asyncio
    async def test_점진적_이동_완료_후_목표값_도달(self):
        """이동 완료 후 목표 위치에 정확히 도달해야 함 / Should reach target position after movement"""
        actuator = ActuatorController(simulation=True)
        target = {"head_left": 60, "head_right": 10, "foot_left": 60, "foot_right": 10}

        await actuator.move_to_position(
            target_name="좌측와위 테스트",
            target_values=target,
            steps=5,  # 테스트 속도를 위해 5단계만 / Only 5 steps for test speed
            step_delay=0.01,
        )

        for actuator_name, target_pct in target.items():
            assert actuator.current_positions[actuator_name] == target_pct, \
                f"{actuator_name}: 예상 {target_pct}, 실제 {actuator.current_positions[actuator_name]}"

    def test_긴급_정지_시뮬레이션(self):
        """긴급 정지가 시뮬레이션에서 오류 없이 실행되어야 함 / Emergency stop should work without errors"""
        actuator = ActuatorController(simulation=True)
        actuator.emergency_stop()  # 오류 없이 실행되어야 함 / Should run without errors


# ─────────────────────────────────────────────
# 안전 검사 테스트 / Safety Check Tests
# ─────────────────────────────────────────────
class TestSafetyChecker:

    @pytest.mark.asyncio
    async def test_시뮬레이션_모드_안전검사_통과(self):
        """시뮬레이션 모드에서는 모든 안전 검사 통과 / All checks pass in simulation mode"""
        safety = SafetyChecker(simulation=True)
        is_safe, reason = await safety.is_safe_to_move()
        assert is_safe is True
        assert "통과" in reason or "passed" in reason.lower()


# ─────────────────────────────────────────────
# 스케줄러 테스트 / Scheduler Tests
# ─────────────────────────────────────────────
class TestPositionScheduler:

    def test_초기_자세가_앙와위(self):
        """스케줄러 초기 자세가 앙와위 / Initial position should be supine"""
        actuator = ActuatorController(simulation=True)
        safety = SafetyChecker(simulation=True)
        scheduler = PositionScheduler(actuator=actuator, safety=safety)
        assert scheduler.current_position == Position.SUPINE

    def test_자세_순환_순서_정확성(self):
        """자세 순환 순서가 올바른지 확인 / Verify position rotation sequence"""
        expected = [Position.SUPINE, Position.LEFT_LATERAL, Position.SUPINE, Position.RIGHT_LATERAL]
        assert POSITION_ROTATION == expected, "자세 순환 순서가 잘못되었습니다 / Rotation sequence is incorrect"

    def test_일시정지_재개_동작(self):
        """일시정지 및 재개가 올바르게 동작 / Pause and resume should work correctly"""
        actuator = ActuatorController(simulation=True)
        safety = SafetyChecker(simulation=True)
        scheduler = PositionScheduler(actuator=actuator, safety=safety)

        assert scheduler.is_paused is False
        scheduler.pause()
        assert scheduler.is_paused is True
        scheduler.resume()
        assert scheduler.is_paused is False

    def test_상태_반환_딕셔너리_구조(self):
        """get_status()가 올바른 구조의 딕셔너리를 반환해야 함"""
        actuator = ActuatorController(simulation=True)
        safety = SafetyChecker(simulation=True)
        scheduler = PositionScheduler(actuator=actuator, safety=safety)

        status = scheduler.get_status()

        required_keys = [
            "is_running", "is_paused", "current_position",
            "current_position_ko", "total_rotations", "rotation_interval_minutes"
        ]
        for key in required_keys:
            assert key in status, f"status에 '{key}' 키가 없습니다 / '{key}' key missing from status"

    @pytest.mark.asyncio
    async def test_자세_변환_완료_후_카운터_증가(self):
        """자세 변환 완료 후 total_rotations 증가 / total_rotations should increment after rotation"""
        actuator = ActuatorController(simulation=True)
        safety = SafetyChecker(simulation=True)

        alert_called = False
        async def mock_alert(level, message, requires_manual):
            nonlocal alert_called
            alert_called = True

        scheduler = PositionScheduler(
            actuator=actuator,
            safety=safety,
            alert_callback=mock_alert,
        )

        initial_count = scheduler.total_rotations
        await scheduler._perform_rotation()

        assert scheduler.total_rotations == initial_count + 1, \
            "자세 변환 후 카운터가 증가되지 않았습니다 / Rotation counter did not increment"
        assert alert_called, "보호자 알림이 호출되지 않았습니다 / Caregiver alert was not called"


# ─────────────────────────────────────────────
# 자세 정의 테스트 / Position Definition Tests
# ─────────────────────────────────────────────
class TestPositionDefinitions:

    def test_모든_자세에_한국어_이름_존재(self):
        """모든 자세에 한국어 이름이 정의되어야 함 / All positions should have Korean names"""
        for pos in Position:
            assert pos in POSITION_NAMES_KO, \
                f"{pos.value}에 한국어 이름이 없습니다 / No Korean name for {pos.value}"

    def test_모든_자세에_액추에이터_목표값_존재(self):
        """모든 자세에 액추에이터 목표값이 정의되어야 함 / All positions should have actuator targets"""
        required_actuators = {"head_left", "head_right", "foot_left", "foot_right"}
        for pos in Position:
            assert pos in POSITION_TARGETS, \
                f"{pos.value}에 목표값이 없습니다 / No target values for {pos.value}"
            assert set(POSITION_TARGETS[pos].keys()) == required_actuators, \
                f"{pos.value}의 액추에이터 목표값이 불완전합니다 / Incomplete actuator targets for {pos.value}"

    def test_앙와위_목표값_모두_0(self):
        """앙와위(등 대고 누운 자세)의 모든 액추에이터 목표값은 0이어야 함"""
        for actuator_name, value in POSITION_TARGETS[Position.SUPINE].items():
            assert value == 0, f"앙와위 {actuator_name} 값이 0이 아닙니다 / Supine {actuator_name} is not 0"

    def test_액추에이터_목표값_범위_0_100(self):
        """모든 액추에이터 목표값은 0~100 범위 내여야 함 / All target values should be 0-100"""
        for pos, targets in POSITION_TARGETS.items():
            for actuator_name, value in targets.items():
                assert 0 <= value <= 100, \
                    f"{pos.value}.{actuator_name} 값 {value}이 0~100 범위를 벗어남 / Value out of 0-100 range"


if __name__ == "__main__":
    # pytest 없이 직접 실행 시 / Direct run without pytest
    import asyncio

    async def run_tests():
        print("🧪 CareBot 단위 테스트 실행 중... / Running unit tests...")

        # 액추에이터 테스트
        t1 = TestActuatorController()
        t1.test_초기화_시_모든_액추에이터_0위치()
        print("✅ 액추에이터 초기화 테스트 통과")

        await t1.test_점진적_이동_완료_후_목표값_도달()
        print("✅ 점진적 이동 테스트 통과")

        # 스케줄러 테스트
        t2 = TestPositionScheduler()
        t2.test_초기_자세가_앙와위()
        t2.test_자세_순환_순서_정확성()
        t2.test_일시정지_재개_동작()
        t2.test_상태_반환_딕셔너리_구조()
        await t2.test_자세_변환_완료_후_카운터_증가()
        print("✅ 스케줄러 테스트 통과")

        # 자세 정의 테스트
        t3 = TestPositionDefinitions()
        t3.test_모든_자세에_한국어_이름_존재()
        t3.test_모든_자세에_액추에이터_목표값_존재()
        t3.test_앙와위_목표값_모두_0()
        t3.test_액추에이터_목표값_범위_0_100()
        print("✅ 자세 정의 테스트 통과")

        print("\n🎉 모든 테스트 통과! / All tests passed!")

    asyncio.run(run_tests())
