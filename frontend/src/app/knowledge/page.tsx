import { Sidebar } from '@/components/Sidebar'
import { FileUpload } from '@/components/upload/FileUpload'

export default function KnowledgePage() {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <main className="flex-1 px-8 py-8" style={{ background: 'var(--bg)' }}>
        <div className="mx-auto max-w-3xl">
          <h1 className="mb-2 text-2xl font-bold">知识库</h1>
          <p className="mb-8" style={{ color: 'var(--text-secondary)' }}>
            上传 PDF、TXT 或 Markdown 文档，AI 会自动理解内容
          </p>
          <FileUpload />
        </div>
      </main>
    </div>
  )
}
