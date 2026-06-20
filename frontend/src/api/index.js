/**
 * LingoForge API Client
 *
 * 统一管理所有后端 API 调用。
 * 身份通过请求头绑定，禁止在请求体中传递 user_id / session_id。
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

// ---- 内部工具 ----

let _demoUserId = 1
let _sessionId = null

export function setDemoUserId(id) {
  _demoUserId = id
}

export function getDemoUserId() {
  return _demoUserId
}

export function setSessionId(id) {
  _sessionId = id
}

export function getSessionId() {
  return _sessionId
}

function authHeaders() {
  const headers = {
    'Content-Type': 'application/json',
    'X-LingoForge-User-Id': String(_demoUserId),
  }
  if (_sessionId != null) {
    headers['X-LingoForge-Session-Id'] = String(_sessionId)
  }
  return headers
}

async function request(method, path, body = null) {
  const opts = { method, headers: authHeaders() }
  if (body != null) {
    opts.body = JSON.stringify(body)
  }

  let response
  try {
    response = await fetch(`${API_BASE_URL}${path}`, opts)
  } catch (err) {
    throw new ApiError('NETWORK_ERROR', '无法连接到后端服务，请确认 FastAPI 已启动。', {})
  }

  if (!response.ok) {
    let detail = {}
    try {
      const json = await response.json()
      detail = json.detail || json
    } catch (_) {
      // 非 JSON 响应
    }
    const code = detail.code || `HTTP_${response.status}`
    const message = detail.message || `请求失败（${response.status}）`
    const details = detail.details || {}
    throw new ApiError(code, message, details)
  }

  return response.json()
}

// ---- 自定义错误 ----

export class ApiError extends Error {
  constructor(code, message, details = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.details = details
  }
}

// ---- 健康检查 ----

export function fetchHealth() {
  return request('GET', '/health')
}

// ---- 用户画像 ----

export function getProfileSummary() {
  return request('GET', '/api/profile/summary')
}

export function saveProfileGoal(data) {
  return request('POST', '/api/profile/goal', data)
}

// ---- 训练会话 ----

export function createTrainingSession(stage = 'FIRST_MAIN') {
  return request('POST', '/api/training/sessions', { stage })
}

export function listTrainingSessions() {
  return request('GET', '/api/training/sessions')
}

// ---- 文本分析与训练任务 ----

export function analyzeText(data) {
  return request('POST', '/api/learning/analyze-text', data)
}

export function analyzeTextAndCreateTask(data) {
  return request('POST', '/api/learning/analyze-text/create-task', data)
}

// ---- 训练任务 ----

export function getSessionTasks(sessionId) {
  return request('GET', `/api/training/sessions/${sessionId}/tasks`)
}

export function getTaskDetail(taskId) {
  return request('GET', `/api/training/tasks/${taskId}`)
}

export function submitTrainingTask(taskId, data) {
  return request('POST', `/api/training/tasks/${taskId}/submit`, data)
}

export function getTaskResult(taskId) {
  return request('GET', `/api/training/tasks/${taskId}/result`)
}

// ---- Agent ----

export function runAgentWorkflow(data) {
  return request('POST', '/api/agent/workflow/text-training', data)
}

// ---- 副线 ----

export function completeAirportTicket(data) {
  return request('POST', '/api/sidequest/airport-ticket/complete', data)
}

// ---- 隔离测试 ----

export function startIsolatedTest(data) {
  return request('POST', '/api/isolated-tests/start', data)
}

export function submitIsolatedTest(attemptId, data) {
  return request('POST', `/api/isolated-tests/attempts/${attemptId}/submit`, data)
}

export { API_BASE_URL }
