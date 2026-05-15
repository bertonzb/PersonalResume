import Link from 'next/link'
import { Sidebar } from '@/components/Sidebar'
import { HealthStatus } from './_components/HealthStatus'

const features = [
  {
    href: '/chat',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0052d9" strokeWidth="1.5">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    title: '智能对话',
    desc: '基于知识库的 RAG 问答，AI 读懂你的每一份文档',
  },
  {
    href: '/knowledge',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0052d9" strokeWidth="1.5">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
      </svg>
    ),
    title: '知识库管理',
    desc: '上传 PDF、TXT、Markdown，自动向量化入库',
  },
  {
    href: '/chat',
    icon: (
      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0052d9" strokeWidth="1.5">
        <circle cx="12" cy="12" r="10" />
        <path d="M12 6v6l4 2" />
      </svg>
    ),
    title: '深度研究',
    desc: 'Agent 自动拆解问题、多步推理、引用来源',
  },
]

export default function HomePage() {
  return (
    <div className="flex min-h-screen">
      {/* 侧边栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col items-center justify-center px-8 py-16">
        {/* Hero */}
        <div className="mb-12 text-center">
          <h1 className="mb-3 text-4xl font-bold tracking-tight">
            <span style={{ color: '#0052d9' }}>Deep</span>Scribe
          </h1>
          <p className="text-lg" style={{ color: '#6b7280' }}>
            个人知识库深度研究助手 · AI 驱动的智能知识管理
          </p>
        </div>

        {/* 功能卡片 */}
        <div className="grid gap-6 sm:grid-cols-3 w-full max-w-3xl">
          {features.map((item) => (
            <Link key={item.title} href={item.href} className="hero-card">
              <div className="mb-3">{item.icon}</div>
              <h2 className="mb-1 text-base font-semibold">{item.title}</h2>
              <p className="text-sm" style={{ color: '#6b7280' }}>
                {item.desc}
              </p>
            </Link>
          ))}
        </div>

        {/* 健康状态 */}
        <div className="mt-12">
          <HealthStatus />
        </div>
      </main>
    </div>
  )
}
