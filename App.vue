<!--
  CareBot 대시보드 — 메인 Vue 3 애플리케이션
  CareBot Dashboard — Main Vue 3 Application

  실시간으로 로봇 상태를 모니터링하고 제어하는 보호자/의료진용 인터페이스
  Interface for caregivers/medical staff to monitor and control the robot in real-time
-->
<template>
  <div class="min-h-screen bg-gray-950 text-white font-sans">

    <!-- 헤더 / Header -->
    <header class="bg-gray-900 border-b border-gray-800 px-6 py-4">
      <div class="max-w-6xl mx-auto flex items-center justify-between">
        <div class="flex items-center gap-3">
          <!-- 로봇 상태 표시기 / Robot status indicator -->
          <div
            class="w-3 h-3 rounded-full animate-pulse"
            :class="{
              'bg-green-400': connectionStatus === 'connected' && !isEmergencyStopped,
              'bg-yellow-400': status?.is_paused,
              'bg-red-500': isEmergencyStopped || connectionStatus === 'disconnected',
            }"
          ></div>
          <h1 class="text-xl font-bold text-white">🏥 CareBot</h1>
          <span class="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">
            욕창 방지 자세 변환 시스템
          </span>
        </div>
        <div class="flex items-center gap-2 text-sm text-gray-400">
          <span>{{ currentTime }}</span>
          <span class="text-gray-600">|</span>
          <span :class="connectionStatus === 'connected' ? 'text-green-400' : 'text-red-400'">
            {{ connectionStatus === 'connected' ? '● 연결됨' : '○ 연결 끊김' }}
          </span>
        </div>
      </div>
    </header>

    <main class="max-w-6xl mx-auto px-6 py-8 space-y-6">

      <!-- 긴급 정지 버튼 / Emergency Stop Button -->
      <div
        v-if="isEmergencyStopped"
        class="bg-red-900/50 border border-red-500 rounded-xl p-4 flex items-center justify-between"
      >
        <div class="flex items-center gap-3">
          <span class="text-2xl">🚨</span>
          <div>
            <p class="font-bold text-red-300">긴급 정지 상태</p>
            <p class="text-sm text-red-400">수동 확인 후 재개하세요 / Manual check required before resuming</p>
          </div>
        </div>
        <button
          @click="resumeAfterEmergency"
          class="bg-red-600 hover:bg-red-500 text-white font-bold px-4 py-2 rounded-lg transition"
        >
          재개
        </button>
      </div>

      <!-- 상태 카드 그리드 / Status Card Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">

        <!-- 현재 자세 카드 / Current Position Card -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">현재 자세</p>
          <div class="flex items-center gap-3 mt-2">
            <span class="text-4xl">{{ currentPositionEmoji }}</span>
            <div>
              <p class="text-lg font-bold text-white">{{ status?.current_position_ko || '로딩 중...' }}</p>
              <p class="text-xs text-gray-500">{{ status?.current_position }}</p>
            </div>
          </div>
        </div>

        <!-- 다음 변환까지 / Next Rotation Countdown -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">다음 자세 변환까지</p>
          <p class="text-3xl font-mono font-bold text-blue-400 mt-2">{{ nextRotationCountdown }}</p>
          <p class="text-xs text-gray-500 mt-1">
            {{ status?.is_paused ? '⏸️ 일시정지 중' : '자동 변환 예정' }}
          </p>
        </div>

        <!-- 총 변환 횟수 / Total Rotations -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">오늘 자세 변환 횟수</p>
          <p class="text-3xl font-bold text-green-400 mt-2">{{ status?.total_rotations ?? '--' }}회</p>
          <p class="text-xs text-gray-500 mt-1">욕창 예방 권장: 12회/일</p>
        </div>

      </div>

      <!-- 제어 패널 + 로그 패널 / Control Panel + Log Panel -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

        <!-- 수동 제어 패널 / Manual Control Panel -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 class="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            🎮 수동 제어 <span class="text-gray-600 font-normal">/ Manual Control</span>
          </h2>

          <!-- 자세 변환 버튼들 / Position Change Buttons -->
          <div class="space-y-3">
            <button
              v-for="pos in positions"
              :key="pos.value"
              @click="rotateToPosition(pos.value)"
              :disabled="isMoving || isEmergencyStopped"
              class="w-full flex items-center justify-between bg-gray-800 hover:bg-gray-700
                     disabled:opacity-40 disabled:cursor-not-allowed
                     border border-gray-700 rounded-lg px-4 py-3 transition group"
              :class="{ 'border-blue-500 bg-blue-900/20': status?.current_position === pos.value }"
            >
              <div class="flex items-center gap-3">
                <span class="text-2xl">{{ pos.emoji }}</span>
                <div class="text-left">
                  <p class="text-sm font-medium text-white">{{ pos.nameKo }}</p>
                  <p class="text-xs text-gray-500">{{ pos.nameEn }}</p>
                </div>
              </div>
              <span
                v-if="status?.current_position === pos.value"
                class="text-xs text-blue-400 font-medium"
              >현재</span>
              <span v-else class="text-xs text-gray-600 group-hover:text-gray-400">변환 →</span>
            </button>
          </div>

          <!-- 스케줄 제어 / Schedule Control -->
          <div class="mt-4 pt-4 border-t border-gray-800 flex gap-3">
            <button
              v-if="!status?.is_paused"
              @click="pauseSchedule"
              class="flex-1 bg-yellow-900/40 hover:bg-yellow-900/60 border border-yellow-700
                     text-yellow-300 text-sm font-medium py-2 rounded-lg transition"
            >
              ⏸️ 스케줄 정지
            </button>
            <button
              v-else
              @click="resumeSchedule"
              class="flex-1 bg-green-900/40 hover:bg-green-900/60 border border-green-700
                     text-green-300 text-sm font-medium py-2 rounded-lg transition"
            >
              ▶️ 스케줄 재개
            </button>
            <button
              @click="triggerEmergencyStop"
              class="flex-1 bg-red-900/40 hover:bg-red-900/60 border border-red-700
                     text-red-300 text-sm font-medium py-2 rounded-lg transition"
            >
              🚨 긴급 정지
            </button>
          </div>
        </div>

        <!-- 실시간 이벤트 로그 / Real-time Event Log -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 class="text-sm font-semibold text-gray-300 mb-4 flex items-center gap-2">
            📋 실시간 로그 <span class="text-gray-600 font-normal">/ Live Log</span>
          </h2>

          <div class="space-y-2 max-h-72 overflow-y-auto custom-scroll">
            <div
              v-if="eventLogs.length === 0"
              class="text-gray-600 text-sm text-center py-8"
            >
              로그가 없습니다 / No logs yet
            </div>
            <div
              v-for="(log, i) in eventLogs"
              :key="i"
              class="flex items-start gap-2 text-sm p-2 rounded-lg"
              :class="logRowClass(log.level)"
            >
              <span class="text-xs font-mono text-gray-500 mt-0.5 whitespace-nowrap">
                {{ formatLogTime(log.time) }}
              </span>
              <span class="text-xs mt-0.5">{{ logLevelEmoji(log.level) }}</span>
              <span class="text-gray-300">{{ log.message }}</span>
            </div>
          </div>
        </div>

      </div>

      <!-- AI 분석 패널 / AI Analysis Panel -->
      <div class="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-sm font-semibold text-gray-300 flex items-center gap-2">
            🤖 AI 상태 분석
            <span class="text-gray-600 font-normal">/ AI Status Analysis (Claude)</span>
          </h2>
          <button
            @click="fetchAiSummary"
            :disabled="isLoadingAi"
            class="text-xs bg-blue-900/40 hover:bg-blue-900/70 border border-blue-700
                   text-blue-300 px-3 py-1 rounded-lg transition disabled:opacity-40"
          >
            {{ isLoadingAi ? '분석 중...' : '🔄 재분석' }}
          </button>
        </div>
        <div
          v-if="aiSummary"
          class="bg-gray-950 rounded-lg p-4 text-sm text-gray-300 whitespace-pre-wrap leading-relaxed"
        >{{ aiSummary }}</div>
        <div v-else class="text-gray-600 text-sm text-center py-6">
          '재분석' 버튼을 눌러 AI 분석을 시작하세요 / Click 'Re-analyze' to start AI analysis
        </div>
      </div>

    </main>

    <!-- 이동 중 오버레이 / Moving Overlay -->
    <div
      v-if="isMoving"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
    >
      <div class="bg-gray-900 border border-gray-700 rounded-2xl p-8 text-center max-w-sm">
        <div class="text-5xl mb-4 animate-bounce">🦾</div>
        <p class="text-lg font-bold text-white mb-2">자세 변환 중</p>
        <p class="text-sm text-gray-400">천천히 이동 중입니다. 환자 곁에 있어 주세요.</p>
        <p class="text-xs text-gray-600 mt-1">Position changing — please stay with patient</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// ─────────────────────────────────────────────
// 상태 / State
// ─────────────────────────────────────────────
const status = ref(null)
const eventLogs = ref([])
const aiSummary = ref(null)
const connectionStatus = ref('disconnected')
const isMoving = ref(false)
const isEmergencyStopped = ref(false)
const isLoadingAi = ref(false)
const currentTime = ref('')

// API 기본 URL / API base URL
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

// 자세 목록 / Position list
const positions = [
  { value: 'supine',         nameKo: '앙와위',        nameEn: 'Supine',         emoji: '🛏️' },
  { value: 'left_lateral',   nameKo: '좌측와위 (30°)', nameEn: 'Left Lateral',   emoji: '↩️' },
  { value: 'right_lateral',  nameKo: '우측와위 (30°)', nameEn: 'Right Lateral',  emoji: '↪️' },
]

// ─────────────────────────────────────────────
// Computed
// ─────────────────────────────────────────────
const currentPositionEmoji = computed(() => {
  const pos = positions.find(p => p.value === status.value?.current_position)
  return pos?.emoji || '❓'
})

const nextRotationCountdown = computed(() => {
  if (!status.value?.next_rotation_time) return '--:--'
  if (status.value?.is_paused) return '⏸️ --:--'
  const next = new Date(status.value.next_rotation_time)
  const diff = Math.max(0, next - Date.now())
  const mins = Math.floor(diff / 60000)
  const secs = Math.floor((diff % 60000) / 1000)
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
})

// ─────────────────────────────────────────────
// WebSocket 연결 / WebSocket Connection
// ─────────────────────────────────────────────
let ws = null
let reconnectTimer = null

function connectWebSocket() {
  const wsUrl = API_BASE.replace('http', 'ws') + '/ws'
  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    connectionStatus.value = 'connected'
    clearTimeout(reconnectTimer)
  }

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data)

    if (msg.type === 'initial_status' || msg.type === 'status_update') {
      status.value = msg.data
    } else if (msg.type === 'alert') {
      // 새 이벤트 로그 추가 (최대 100건 유지)
      // Add new event log (keep max 100 entries)
      eventLogs.value.unshift(msg.data)
      if (eventLogs.value.length > 100) eventLogs.value.pop()
    } else if (msg.type === 'emergency_stop') {
      isEmergencyStopped.value = true
      isMoving.value = false
    }
  }

  ws.onclose = () => {
    connectionStatus.value = 'disconnected'
    // 5초 후 재연결 시도 / Reconnect after 5 seconds
    reconnectTimer = setTimeout(connectWebSocket, 5000)
  }

  ws.onerror = () => {
    ws?.close()
  }

  // 30초마다 핑 전송 / Send ping every 30 seconds
  setInterval(() => {
    if (ws?.readyState === WebSocket.OPEN) ws.send('ping')
  }, 30000)
}

// ─────────────────────────────────────────────
// API 호출 / API Calls
// ─────────────────────────────────────────────

/** 초기 상태 불러오기 / Fetch initial status */
async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`)
    const data = await res.json()
    if (data.success) status.value = data.data
  } catch (e) {
    console.error('상태 불러오기 실패 / Status fetch failed:', e)
  }
}

/** 특정 자세로 변환 / Rotate to specific position */
async function rotateToPosition(positionValue) {
  if (isMoving.value) return
  isMoving.value = true

  try {
    const res = await fetch(`${API_BASE}/api/position/rotate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ position: positionValue, reason: '수동 변환 / Manual rotation' }),
    })
    const data = await res.json()

    if (!data.success) {
      alert(`자세 변환 실패: ${data.detail || '알 수 없는 오류'}`)
      isMoving.value = false
    } else {
      // 변환 완료 예상 시간 후 오버레이 제거 (20초)
      // Remove overlay after expected completion time (20 seconds)
      setTimeout(() => { isMoving.value = false }, 20000)
    }
  } catch (e) {
    console.error('자세 변환 요청 실패 / Rotation request failed:', e)
    isMoving.value = false
  }
}

/** 긴급 정지 / Emergency stop */
async function triggerEmergencyStop() {
  if (!confirm('🚨 긴급 정지를 실행하시겠습니까? / Execute emergency stop?')) return

  try {
    await fetch(`${API_BASE}/api/emergency-stop`, { method: 'POST' })
    isEmergencyStopped.value = true
    isMoving.value = false
  } catch (e) {
    console.error(e)
  }
}

/** 긴급 정지 후 재개 / Resume after emergency stop */
async function resumeAfterEmergency() {
  isEmergencyStopped.value = false
  await resumeSchedule()
}

/** 스케줄 일시정지 / Pause schedule */
async function pauseSchedule() {
  await fetch(`${API_BASE}/api/scheduler/pause`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  await fetchStatus()
}

/** 스케줄 재개 / Resume schedule */
async function resumeSchedule() {
  await fetch(`${API_BASE}/api/scheduler/resume`, { method: 'POST' })
  await fetchStatus()
}

/** AI 분석 / AI analysis */
async function fetchAiSummary() {
  isLoadingAi.value = true
  try {
    const res = await fetch(`${API_BASE}/api/ai/summary`)
    const data = await res.json()
    if (data.success) {
      aiSummary.value = data.data.summary
    }
  } catch (e) {
    aiSummary.value = 'AI 분석 중 오류가 발생했습니다. / AI analysis error occurred.'
  } finally {
    isLoadingAi.value = false
  }
}

// ─────────────────────────────────────────────
// 유틸리티 / Utilities
// ─────────────────────────────────────────────
function formatLogTime(isoString) {
  return new Date(isoString).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function logLevelEmoji(level) {
  return { info: '✅', warning: '⚠️', critical: '🚨', error: '❌' }[level] || '•'
}

function logRowClass(level) {
  return {
    info: 'bg-gray-800/30',
    warning: 'bg-yellow-900/20',
    critical: 'bg-red-900/30',
    error: 'bg-red-900/30',
  }[level] || ''
}

// ─────────────────────────────────────────────
// 생명주기 / Lifecycle
// ─────────────────────────────────────────────
onMounted(() => {
  fetchStatus()
  connectWebSocket()

  // 현재 시각 업데이트 (매초)
  // Update current time every second
  const timeInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('ko-KR')
  }, 1000)

  // 상태 폴링 (5초마다 — WebSocket 보조용)
  // Status polling every 5 seconds (as WebSocket backup)
  const pollInterval = setInterval(fetchStatus, 5000)

  onUnmounted(() => {
    clearInterval(timeInterval)
    clearInterval(pollInterval)
    clearTimeout(reconnectTimer)
    ws?.close()
  })
})
</script>

<style scoped>
.custom-scroll::-webkit-scrollbar {
  width: 4px;
}
.custom-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: #374151;
  border-radius: 2px;
}
</style>
