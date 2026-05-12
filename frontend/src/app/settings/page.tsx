export default function SettingsPage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">设置</h1>
      <div className="space-y-6">
        <div className="rounded-lg border p-6">
          <h2 className="mb-2 text-lg font-medium">API 连接</h2>
          <p className="text-sm text-gray-500">
            后端 API 地址: {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}
          </p>
        </div>
        <div className="rounded-lg border p-6">
          <h2 className="mb-2 text-lg font-medium">关于</h2>
          <p className="text-sm text-gray-500">DeepScribe v0.1.0 — 个人知识库深度研究助手</p>
        </div>
      </div>
    </main>
  )
}
