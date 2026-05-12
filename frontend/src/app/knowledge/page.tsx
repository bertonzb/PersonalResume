import { FileUpload } from '@/components/upload/FileUpload'

export default function KnowledgePage() {
  return (
    <main className="mx-auto max-w-4xl px-4 py-8">
      <h1 className="mb-6 text-2xl font-bold">知识库</h1>
      <FileUpload />
      <div className="mt-8">
        <p className="text-sm text-gray-400">上传的文档将显示在这里</p>
      </div>
    </main>
  )
}
