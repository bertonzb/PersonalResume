import Link from 'next/link'
import { HealthStatus } from './_components/HealthStatus'

const navItems = [
  { href: '/chat', label: '对话', desc: '与 AI 助手对话，基于知识库问答' },
  { href: '/knowledge', label: '知识库', desc: '上传和管理文档' },
  { href: '/settings', label: '设置', desc: '查看系统配置和版本' },
]

export default function HomePage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-12">
      <h1 className="mb-2 text-3xl font-bold">DeepScribe</h1>
      <p className="mb-8 text-gray-500">个人知识库深度研究助手</p>

      {/* 导航卡片 */}
      <div className="mb-8 grid gap-4 sm:grid-cols-3">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-lg border p-6 transition-shadow hover:shadow-md"
          >
            <h2 className="mb-1 text-lg font-medium">{item.label}</h2>
            <p className="text-sm text-gray-400">{item.desc}</p>
          </Link>
        ))}
      </div>

      <HealthStatus />
    </main>
  )
}
