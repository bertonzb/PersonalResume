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

  if (!message.content) {
    return null
  }

  return (
    <div className={cn('flex gap-3 py-3', isUser && 'flex-row-reverse', className)}>
      {/* 头像 */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-medium',
          isUser ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600',
        )}
      >
        {isUser ? 'U' : 'AI'}
      </div>

      {/* 消息内容 */}
      <div className="max-w-[70%]">
        <div
          className={cn(
            'rounded-lg px-4 py-2.5 text-sm leading-relaxed',
            isUser ? 'bg-blue-500 text-white' : 'bg-white border',
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* 引用来源 */}
        {message.sources && message.sources.length > 0 && (
          <div className="mt-1 space-y-0.5">
            {message.sources.map((s, i) => (
              <div key={s.chunkId} className="text-xs text-gray-400">
                来源 {i + 1}: {s.content.slice(0, 80)}... (相关度: {s.score})
              </div>
            ))}
          </div>
        )}

        {/* 错误重试 */}
        {message.status === 'error' && (
          <Button size="small" onClick={handleRetry} className="mt-1">
            重试
          </Button>
        )}
      </div>
    </div>
  )
}
