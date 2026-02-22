"""
CareBot AI 서비스 — Claude API 기반 환자 상태 분석
CareBot AI Service — Patient status analysis powered by Claude API

환자 자세 변환 기록을 분석하여 보호자/의료진에게 요약 제공
Analyzes position change logs to provide summaries for caregivers/medical staff
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional
import httpx

# Anthropic API 설정 / Anthropic API configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
AI_MODEL = "claude-sonnet-4-6"  # 효율적인 모델 사용 / Use efficient model


async def get_patient_summary(logs: list[dict], current_status: dict) -> dict:
    """
    Claude AI를 사용하여 환자 자세 변환 현황 요약 생성
    Generate patient repositioning status summary using Claude AI

    Args:
        logs: 자세 변환 기록 목록 / Position change log list
        current_status: 현재 로봇 상태 / Current robot status

    Returns:
        AI 분석 요약 딕셔너리 / AI analysis summary dictionary
    """
    if not ANTHROPIC_API_KEY:
        # API 키 없으면 기본 요약 반환
        # Return basic summary if no API key
        return _generate_basic_summary(logs, current_status)

    # 최근 24시간 로그만 분석
    # Analyze only last 24 hours of logs
    cutoff = datetime.now() - timedelta(hours=24)
    recent_logs = [
        log for log in logs
        if datetime.fromisoformat(log["time"]) > cutoff
    ]

    # AI 프롬프트 구성
    # Construct AI prompt
    prompt = _build_analysis_prompt(recent_logs, current_status)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": AI_MODEL,
                    "max_tokens": 1000,
                    "system": _get_system_prompt(),
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            ai_text = data["content"][0]["text"]

            return {
                "ai_powered": True,
                "model": AI_MODEL,
                "summary": ai_text,
                "analyzed_logs_count": len(recent_logs),
                "analysis_time": datetime.now().isoformat(),
            }

    except Exception as e:
        # AI 분석 실패 시 기본 요약으로 폴백
        # Fall back to basic summary if AI analysis fails
        basic = _generate_basic_summary(logs, current_status)
        basic["ai_error"] = str(e)
        return basic


def _get_system_prompt() -> str:
    """AI 시스템 프롬프트 / AI system prompt"""
    return """당신은 욕창 방지 로봇 시스템을 모니터링하는 의료 어시스턴트입니다.
주어진 자세 변환 기록과 현재 상태를 분석하여 보호자와 의료진에게 유용한 요약을 제공하세요.

다음 사항을 포함하여 분석하세요:
1. 자세 변환이 정상적으로 수행되고 있는지 여부
2. 이상 패턴이나 주의가 필요한 사항
3. 욕창 예방 관점에서의 현황 평가
4. 보호자에게 전달할 간결한 상태 요약

항상 한국어로 응답하세요. 의학적 결정을 내리지 말고, 로봇 시스템 운영 현황만 보고하세요.

You are a medical assistant monitoring a pressure ulcer prevention robot system.
Analyze the given position change logs and current status to provide useful summaries.
Always respond in Korean. Do not make medical decisions, only report on robot operation status."""


def _build_analysis_prompt(logs: list[dict], current_status: dict) -> str:
    """분석 프롬프트 구성 / Build analysis prompt"""
    logs_summary = json.dumps(logs[-20:], ensure_ascii=False, indent=2)  # 최근 20건
    status_summary = json.dumps(current_status, ensure_ascii=False, indent=2)

    return f"""다음은 지난 24시간 동안의 욕창 방지 로봇 작동 기록입니다.

## 현재 시스템 상태 / Current System Status:
{status_summary}

## 최근 자세 변환 기록 / Recent Position Change Logs (최근 20건):
{logs_summary}

위 데이터를 분석하여 보호자에게 제공할 간결한 상태 요약을 작성해주세요.
총 자세 변환 횟수, 이상 여부, 주의 사항 등을 포함하세요."""


def _generate_basic_summary(logs: list[dict], current_status: dict) -> dict:
    """
    AI 없이 기본 통계 기반 요약 생성
    Generate basic statistics-based summary without AI
    """
    total = len(logs)
    warnings = [l for l in logs if l.get("level") in ("warning", "critical")]
    successful = [l for l in logs if l.get("level") == "info"]

    # 욕창 위험 평가 (단순 규칙 기반)
    # Simple rule-based pressure ulcer risk assessment
    last_rotation = current_status.get("last_rotation_time")
    if last_rotation:
        last_dt = datetime.fromisoformat(last_rotation)
        hours_since = (datetime.now() - last_dt).total_seconds() / 3600
        risk_level = "낮음" if hours_since < 2 else ("중간" if hours_since < 4 else "높음")
    else:
        hours_since = None
        risk_level = "알 수 없음"

    summary_text = f"""📊 CareBot 운영 현황 요약
━━━━━━━━━━━━━━━━━━━━━━━
• 총 자세 변환 횟수: {current_status.get('total_rotations', 0)}회
• 오늘 기록: {total}건 (성공 {len(successful)}건, 경고 {len(warnings)}건)
• 현재 자세: {current_status.get('current_position_ko', '알 수 없음')}
• 마지막 변환 후 경과: {f'{hours_since:.1f}시간' if hours_since is not None else '정보 없음'}
• 욕창 위험도: {risk_level}
• 시스템 상태: {'일시정지' if current_status.get('is_paused') else '정상 운영 중'}

{'⚠️ 주의: 최근 경고가 발생했습니다. 확인이 필요합니다.' if warnings else '✅ 시스템이 정상적으로 운영 중입니다.'}"""

    return {
        "ai_powered": False,
        "summary": summary_text,
        "stats": {
            "total_rotations": current_status.get("total_rotations", 0),
            "warnings_count": len(warnings),
            "successful_count": len(successful),
            "risk_level": risk_level,
            "hours_since_last_rotation": hours_since,
        },
        "analysis_time": datetime.now().isoformat(),
    }
