import { apiRequest } from '@/lib/api'
import type { HealthResponse } from '@/types'

export async function HealthStatus() {
  let status = '检测中...'
  let ok = false

  try {
    const data = await apiRequest<HealthResponse>('/health', {
      // Server Component: 每次请求重新验证
      cache: 'no-store',
    })
    status = `${data.status} (v${data.version})`
    ok = true
  } catch {
    status = '无法连接后端服务'
  }

  return (
    <div
      className="rounded-lg border p-4"
      style={{ borderColor: ok ? '#52c41a' : '#ff4d4f' }}
    >
      <span className="text-sm font-medium">后端状态：</span>
      <span style={{ color: ok ? '#52c41a' : '#ff4d4f' }}>{status}</span>
    </div>
  )
}
