const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchHealth() {
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`健康检查失败：${response.status}`)
  }
  return response.json()
}

export { API_BASE_URL }

