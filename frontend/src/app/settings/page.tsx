import { Sidebar } from '@/components/Sidebar'

export default function SettingsPage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 px-8 py-8" style={{ background: 'var(--bg)' }}>
        <div className="mx-auto max-w-3xl">
          <h1 className="mb-2 text-2xl font-bold">设置</h1>
          <p className="mb-8" style={{ color: 'var(--text-secondary)' }}>
            系统配置和版本信息
          </p>
          <div className="space-y-4">
            <div className="hero-card" onClick={undefined}>
              <h2 className="mb-1 text-base font-semibold">API 连接</h2>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                后端地址: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
              </p>
            </div>
            <div className="hero-card" onClick={undefined}>
              <h2 className="mb-1 text-base font-semibold">关于 DeepScribe</h2>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                v0.1.0 · 基于 RAG + AI Agent 的智能知识管理平台
              </p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
