'use client'

import { useCallback, useState } from 'react'
import { Button, Input } from 'antd'
import { SendOutlined } from '@ant-design/icons'
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
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  return (
    <div className={cn('flex gap-2', className)}>
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="输入你的问题..."
        disabled={disabled}
        autoSize={{ minRows: 1, maxRows: 6 }}
        className="flex-1"
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
      >
        发送
      </Button>
    </div>
  )
}
