'use client'

import { useCallback, useState } from 'react'
import { cn } from '@/lib/utils'

export interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  className?: string
}

export function ChatInput({ onSend, disabled, className }: ChatInputProps) {
  const [value, setValue] = useState('')

  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }, [value, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Enter 发送，Shift+Enter 换行
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  return (
    <div className={cn('chat-input-wrapper', className)}>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
        disabled={disabled}
        rows={1}
        style={{ minHeight: 24, maxHeight: 160 }}
        onInput={(e) => {
          const el = e.currentTarget
          el.style.height = 'auto'
          el.style.height = Math.min(el.scrollHeight, 160) + 'px'
        }}
      />
      <div className="chat-input-actions">
        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
          AI 基于你的知识库回答
        </span>
        <button
          onClick={handleSend}
          disabled={disabled || !value.trim()}
          className="flex items-center justify-center"
          style={{
            width: 32,
            height: 32,
            borderRadius: 8,
            border: 'none',
            background: value.trim() && !disabled ? 'var(--primary)' : '#e5e7eb',
            color: value.trim() && !disabled ? 'white' : '#9ca3af',
            cursor: value.trim() && !disabled ? 'pointer' : 'default',
            transition: 'all 0.2s',
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="22" y1="2" x2="11" y2="13" />
            <polygon points="22 2 15 22 11 13 2 9 22 2" />
          </svg>
        </button>
      </div>
    </div>
  )
}
