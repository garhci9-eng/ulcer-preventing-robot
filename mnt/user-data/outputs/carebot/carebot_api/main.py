"""
CareBot API 서버 — FastAPI 기반 REST API + WebSocket
CareBot API Server — FastAPI-based REST API + WebSocket

대시보드 및 외부 알림 시스템과 통신하는 백엔드 서버
Backend server for dashboard and external notification systems
"""

import asyncio
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 상위 디렉토리에서 carebot_core 임포트
# Import carebot_core from parent directory
sys.path.append(str(Path(__file__).parent.parent))

from carebot_core.main import (
    ActuatorController,
    Position,
    POSITION_NAMES_KO,
    POSITION_TARGETS,
    PositionScheduler,
    SafetyChecker,
    SIMULATION_MODE,
)

# ─────────────────────────────────────────────
# 전역 상태 / Global State
# ─────────────────────────────────────────────
class AppState:
    actuator: Optional[ActuatorController] = None
    scheduler: Optional[PositionScheduler] = None
    safety: Optional[SafetyChecker] = None
    websocket_clients: list[WebSocket] = []
    position_logs: list[dict] = []  # 자세 변환 이력 / Position change history

app_state = AppState()


# ─────────────────────────────────────────────
# 앱 수명 주기 / App Lifecycle
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 로봇 시스템 초기화 / Initialize robot system on app start/stop"""
    # 시작 / Startup
    app_state.actuator = ActuatorController(simulation=SIMULATION_MODE)
    app_state.safety = SafetyChecker(simulation=SIMULATION_MODE)

    async def caregiver_alert(level: str, message: str, requires_manual: bool):
        """보호자 알림 + WebSocket 브로드캐스트"""
        log_entry = {
            "time": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "requires_manual": requires_manual,
        }
        app_state.position_logs.append(log_entry)

        # WebSocket 클라이언트들에게 실시간 알림
        # Broadcast to all WebSocket clients
        await broadcast_to_websockets({"type": "alert", "data": log_entry})

    app_state.scheduler = PositionScheduler(
        actuator=app_state.actuator,
        safety=app_state.safety,
        alert_callback=caregiver_alert,
    )

    # 백그라운드로 스케줄러 시작
    # Start scheduler in background
    asyncio.create_task(app_state.scheduler.start())

    yield

    # 종료 / Shutdown
    if app_state.scheduler:
        app_state.scheduler.stop()
    if app_state.actuator:
        app_state.actuator.cleanup()


# ─────────────────────────────────────────────
# FastAPI 앱 설정 / FastAPI App Configuration
# ─────────────────────────────────────────────
app = FastAPI(
    title="CareBot API",
    description="욕창 방지 자세 변환 로봇 제어 API / Pressure Ulcer Prevention Robot Control API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Pydantic 모델 / Pydantic Models
# ─────────────────────────────────────────────
class RotateRequest(BaseModel):
    position: Optional[str] = None  # None이면 자동 다음 자세 / None = auto next position
    reason: Optional[str] = None    # 수동 변환 사유 / Reason for manual rotation


class PauseRequest(BaseModel):
    duration_minutes: Optional[int] = None  # None이면 무한 정지 / None = indefinite pause


# ─────────────────────────────────────────────
# WebSocket 브로드캐스트 / WebSocket Broadcast
# ─────────────────────────────────────────────
async def broadcast_to_websockets(message: dict):
    """모든 연결된 WebSocket 클라이언트에 메시지 전송"""
    dead_sockets = []
    for ws in app_state.websocket_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead_sockets.append(ws)
    for ws in dead_sockets:
        app_state.websocket_clients.remove(ws)


# ─────────────────────────────────────────────
# API 라우터 / API Routes
# ─────────────────────────────────────────────

@app.get("/", tags=["시스템 / System"])
async def root():
    """API 루트 / API root"""
    return {
        "service": "CareBot API",
        "version": "1.0.0",
        "description": "욕창 방지 자세 변환 로봇 제어 API",
        "mode": "simulation" if SIMULATION_MODE else "hardware",
    }


@app.get("/api/status", tags=["상태 / Status"])
async def get_status():
    """
    현재 로봇 상태 조회
    Get current robot status
    """
    if not app_state.scheduler:
        raise HTTPException(status_code=503, detail="스케줄러가 초기화되지 않았습니다 / Scheduler not initialized")

    status = app_state.scheduler.get_status()

    # 액추에이터 현재 위치 추가
    # Add current actuator positions
    status["actuator_positions"] = app_state.actuator.current_positions if app_state.actuator else {}

    return JSONResponse(content={
        "success": True,
        "data": status,
        "timestamp": datetime.now().isoformat(),
    })


@app.post("/api/position/rotate", tags=["자세 제어 / Position Control"])
async def manual_rotate(request: RotateRequest):
    """
    수동 자세 변환 트리거
    Manually trigger position rotation

    보호자 또는 의료진이 즉시 자세 변환이 필요할 때 사용
    Used when caregiver or medical staff needs immediate repositioning
    """
    scheduler = app_state.scheduler
    if not scheduler:
        raise HTTPException(status_code=503, detail="서비스 준비 중입니다 / Service not ready")

    # 안전 검사 먼저 수행
    # Perform safety check first
    is_safe, reason = await app_state.safety.is_safe_to_move()
    if not is_safe:
        raise HTTPException(
            status_code=409,
            detail=f"안전 검사 실패 / Safety check failed: {reason}",
        )

    # 특정 자세 또는 자동 다음 자세로 이동
    # Move to specific or auto-next position
    if request.position:
        try:
            target_pos = Position(request.position)
        except ValueError:
            valid = [p.value for p in Position]
            raise HTTPException(
                status_code=400,
                detail=f"유효하지 않은 자세 / Invalid position. Valid: {valid}",
            )
    else:
        # 자동 다음 자세 결정
        from carebot_core.main import POSITION_ROTATION
        next_idx = (scheduler.rotation_index + 1) % len(POSITION_ROTATION)
        target_pos = POSITION_ROTATION[next_idx]

    # 비동기로 자세 변환 실행 (요청은 즉시 반환)
    # Execute position change asynchronously (request returns immediately)
    asyncio.create_task(scheduler._apply_position(target_pos))

    return JSONResponse(content={
        "success": True,
        "message": f"자세 변환 시작됨 / Position change initiated: {POSITION_NAMES_KO[target_pos]}",
        "target_position": target_pos.value,
        "target_position_ko": POSITION_NAMES_KO[target_pos],
        "reason": request.reason or "수동 변환 / Manual rotation",
    })


@app.post("/api/emergency-stop", tags=["안전 / Safety"])
async def emergency_stop():
    """
    긴급 정지 — 모든 액추에이터 즉시 정지
    Emergency stop — Halt all actuators immediately
    """
    if app_state.actuator:
        app_state.actuator.emergency_stop()
    if app_state.scheduler:
        app_state.scheduler.pause()

    # 모든 대시보드에 긴급 정지 알림
    await broadcast_to_websockets({
        "type": "emergency_stop",
        "data": {
            "time": datetime.now().isoformat(),
            "message": "긴급 정지 실행됨 / Emergency stop executed",
        },
    })

    return JSONResponse(content={
        "success": True,
        "message": "긴급 정지 완료. 수동 확인 후 재개하세요. / Emergency stop complete. Resume after manual check.",
    })


@app.post("/api/scheduler/pause", tags=["스케줄러 / Scheduler"])
async def pause_scheduler(request: PauseRequest):
    """
    자동 자세 변환 스케줄 일시정지
    Pause automatic position rotation schedule

    의료 처치, 식사 등으로 잠시 중단이 필요할 때 사용
    Use when temporary pause needed for medical procedures, meals, etc.
    """
    if not app_state.scheduler:
        raise HTTPException(status_code=503, detail="서비스 준비 중 / Service not ready")

    app_state.scheduler.pause()

    if request.duration_minutes:
        # 지정 시간 후 자동 재개
        # Auto-resume after specified duration
        async def auto_resume():
            await asyncio.sleep(request.duration_minutes * 60)
            if app_state.scheduler:
                app_state.scheduler.resume()

        asyncio.create_task(auto_resume())
        message = f"스케줄 {request.duration_minutes}분 일시정지 / Schedule paused for {request.duration_minutes} minutes"
    else:
        message = "스케줄 일시정지 (수동 재개 필요) / Schedule paused (manual resume required)"

    return JSONResponse(content={"success": True, "message": message})


@app.post("/api/scheduler/resume", tags=["스케줄러 / Scheduler"])
async def resume_scheduler():
    """자동 스케줄 재개 / Resume automatic schedule"""
    if not app_state.scheduler:
        raise HTTPException(status_code=503, detail="서비스 준비 중 / Service not ready")

    app_state.scheduler.resume()
    return JSONResponse(content={
        "success": True,
        "message": "자동 자세 변환 스케줄 재개됨 / Automatic rotation schedule resumed",
    })


@app.get("/api/logs", tags=["기록 / Logs"])
async def get_logs(limit: int = 50):
    """
    자세 변환 기록 조회
    Get position change history logs
    """
    logs = app_state.position_logs[-limit:]  # 최근 N건 / Recent N entries
    return JSONResponse(content={
        "success": True,
        "total": len(app_state.position_logs),
        "data": list(reversed(logs)),  # 최신 순 / Most recent first
    })


@app.get("/api/ai/summary", tags=["AI 분석 / AI Analysis"])
async def get_ai_summary():
    """
    Claude AI 기반 환자 상태 요약 분석
    Patient status summary analysis powered by Claude AI
    """
    from carebot_api.services.ai_service import get_patient_summary
    summary = await get_patient_summary(
        logs=app_state.position_logs,
        current_status=app_state.scheduler.get_status() if app_state.scheduler else {},
    )
    return JSONResponse(content={"success": True, "data": summary})


# ─────────────────────────────────────────────
# WebSocket 실시간 연결 / WebSocket Real-time Connection
# ─────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    실시간 상태 업데이트 WebSocket
    Real-time status update WebSocket

    대시보드가 실시간으로 로봇 상태를 수신하기 위해 사용
    Used by dashboard to receive real-time robot status updates
    """
    await websocket.accept()
    app_state.websocket_clients.append(websocket)

    try:
        # 연결 즉시 현재 상태 전송
        # Send current status immediately on connection
        if app_state.scheduler:
            await websocket.send_json({
                "type": "initial_status",
                "data": app_state.scheduler.get_status(),
            })

        # 연결 유지 (핑/퐁)
        # Keep connection alive (ping/pong)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        if websocket in app_state.websocket_clients:
            app_state.websocket_clients.remove(websocket)
