'use client'

import { useCallback, useRef, useState } from 'react'
import { Spin } from 'antd'
import { ChatBubble } from '@/components/chat/ChatBubble'
import { ChatInput } from '@/components/chat/ChatInput'
import { AgentPanel } from '@/components/agent-panel/AgentPanel'
import type { AgentStep } from '@/types/agent'
import type { ChatMessage, SourceItem } from '@/types/chat'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }, [])

  const handleSend = useCallback(
    async (content: string) => {
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        status: 'done',
        createdAt: new Date().toISOString(),
      }

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        status: 'sending',
        createdAt: new Date().toISOString(),
      }

      setMessages((prev) => [...prev, userMsg, assistantMsg])
      setLoading(true)
      setAgentSteps([])
      scrollToBottom()

      try {
        const res = await fetch(`${API_BASE}/chat/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: content }),
        })

        if (!res.ok) {
          throw new Error(`请求失败: ${res.status}`)
        }

        const data = await res.json()
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? {
                  ...m,
                  content: data.reply,
                  sources: (data.sources || []).map((s: SourceItem) => ({
                    chunkId: s.chunkId,
                    content: s.content,
                    score: s.score,
                  })),
                  status: 'done',
                }
              : m,
          ),
        )

        // 解析 Agent 执行步骤
        if (data.steps && Array.isArray(data.steps)) {
          setAgentSteps(
            data.steps.map((s: { step_number: number; tool_name: string; input: string; output: string; status: string; duration_ms: number }) => ({
              stepNumber: s.step_number,
              toolName: s.tool_name,
              input: s.input,
              output: s.output,
              status: s.status,
              durationMs: s.duration_ms,
            })),
          )
        }
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : '未知错误'
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content: `抱歉，请求失败: ${errMsg}`, status: 'error' }
              : m,
          ),
        )
      } finally {
        setLoading(false)
        scrollToBottom()
      }
    },
    [scrollToBottom],
  )

  return (
    <div className="mx-auto flex h-screen max-w-6xl gap-4 px-4">
      {/* 左侧：对话区 */}
      <div className="flex flex-1 flex-col">
        <div className="border-b py-4">
          <h1 className="text-lg font-bold">对话</h1>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto py-4">
          {messages.length === 0 && (
            <p className="py-12 text-center text-gray-400">上传文档后，在这里开始提问</p>
          )}
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {loading && (
            <div className="py-2 text-center">
              <Spin size="small" />
              <span className="ml-2 text-sm text-gray-400">思考中...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t py-4">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </div>

      {/* 右侧：Agent 面板 */}
      <div className="hidden w-80 shrink-0 overflow-y-auto border-l py-4 pl-4 lg:block">
        <AgentPanel steps={agentSteps} loading={loading} />
      </div>
    </div>
  )
}
