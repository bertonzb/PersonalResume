import { useCallback } from 'react'
import { Button } from 'antd'
import { cn } from '@/lib/utils'
import type { ChatMessage } from '@/types/chat'

export interface ChatBubbleProps {
  message: ChatMessage
  onRetry?: (id: string) => void
  className?: string
}

export function ChatBubble({ message, onRetry, className }: ChatBubbleProps) {
  const isUser = message.role === 'user'

  const handleRetry = useCallback(() => {
    onRetry?.(message.id)
  }, [message.id, onRetry])

  if (!message.content) return null

  return (
    <div className={cn('message-row', isUser ? 'user' : 'assistant', className)}>
      {/* 助手头像（仅 AI 显示在左侧） */}
      {!isUser && (
        <div
          className="flex items-center justify-center shrink-0 mr-3"
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: '#e8f0fe',
            color: '#0052d9',
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          AI
        </div>
      )}

      <div className="message-bubble">
        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* 引用来源 */}
        {message.sources && message.sources.length > 0 && (
          <div className="message-sources">
            {message.sources.map((s, i) => (
              <div key={s.chunkId}>
                来源 {i + 1}: {s.content.slice(0, 80)}...
                <span style={{ marginLeft: 4 }}>({s.score.toFixed(2)})</span>
              </div>
            ))}
          </div>
        )}

        {/* 错误重试 */}
        {message.status === 'error' && (
          <Button size="small" onClick={handleRetry} style={{ marginTop: 8 }}>
            重试
          </Button>
        )}
      </div>

      {/* 用户头像（仅用户显示在右侧） */}
      {isUser && (
        <div
          className="flex items-center justify-center shrink-0 ml-3"
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            background: '#0052d9',
            color: 'white',
            fontSize: 14,
            fontWeight: 700,
          }}
        >
          U
        </div>
      )}
    </div>
  )
}
