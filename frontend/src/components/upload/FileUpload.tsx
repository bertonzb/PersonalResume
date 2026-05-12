'use client'

import { useCallback, useState } from 'react'
import { InboxOutlined } from '@ant-design/icons'
import { message, Upload } from 'antd'

const { Dragger } = Upload

export interface FileUploadProps {
  onUploadSuccess?: (doc: { id: string; filename: string }) => void
  className?: string
}

export function FileUpload({ onUploadSuccess, className }: FileUploadProps) {
  const [uploading, setUploading] = useState(false)

  const handleUpload = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    async (options: any) => {
      const { file, onSuccess, onError } = options
      setUploading(true)

      try {
        const formData = new FormData()
        formData.append('file', file)

        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/documents/upload`,
          {
            method: 'POST',
            body: formData,
          },
        )

        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail || '上传失败')
        }

        const data = await res.json()
        message.success(`"${data.filename}" 上传成功，${data.chunk_count} 个片段已索引`)
        onSuccess?.(data)
        onUploadSuccess?.(data)
      } catch (e) {
        const msg = e instanceof Error ? e.message : '上传失败'
        message.error(msg)
        onError?.(e as Error)
      } finally {
        setUploading(false)
      }
    },
    [onUploadSuccess],
  )

  return (
    <Dragger
      customRequest={handleUpload}
      accept=".pdf,.txt,.md"
      multiple={false}
      disabled={uploading}
      showUploadList={false}
      className={className}
    >
      <p className="text-4xl">
        <InboxOutlined />
      </p>
      <p className="text-base">点击或拖拽文件到此处上传</p>
      <p className="text-sm text-gray-400">支持 PDF、TXT、Markdown，单文件不超过 20MB</p>
    </Dragger>
  )
}
