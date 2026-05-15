'use client'

import { useCallback, useRef, useState } from 'react'
import { Spin } from 'antd'
import { ChatBubble } from '@/components/chat/ChatBubble'
import { ChatInput } from '@/components/chat/ChatInput'
import { AgentPanel } from '@/components/agent-panel/AgentPanel'
import { Sidebar } from '@/components/Sidebar'
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
        const res = await fetch(`${API_BASE}/chat/agent`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: content }),
        })
        if (!res.ok) throw new Error(`请求失败: ${res.status}`)
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
        if (data.steps && Array.isArray(data.steps)) {
          setAgentSteps(
            data.steps.map(
              (s: {
                step_number: number
                tool_name: string
                input: string
                output: string
                status: string
                duration_ms: number
              }) => ({
                stepNumber: s.step_number,
                toolName: s.tool_name,
                input: s.input,
                output: s.output,
                status: s.status,
                durationMs: s.duration_ms,
              }),
            ),
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
    <div className="flex h-screen overflow-hidden">
      {/* 左侧边栏 */}
      <Sidebar />

      {/* 中间对话区 */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* 顶部标题栏 */}
        <div
          className="flex-shrink-0 px-6 py-3 flex items-center gap-3"
          style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}
        >
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              background: 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </div>
          <span className="font-semibold text-sm">DeepScribe 对话</span>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto message-list px-6">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center" style={{ color: 'var(--text-muted)' }}>
                <svg
                  width="64"
                  height="64"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1"
                  style={{ margin: '0 auto 16px', opacity: 0.4 }}
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <p className="text-base font-medium mb-1">开始对话</p>
                <p className="text-sm">上传文档后，向 AI 提问任何关于文档的问题</p>
              </div>
            </div>
          )}
          {messages.map((msg) => (
            <ChatBubble key={msg.id} message={msg} />
          ))}
          {loading && (
            <div className="py-3 text-center">
              <Spin size="small" />
              <span className="ml-2 text-sm" style={{ color: 'var(--text-muted)' }}>
                思考中...
              </span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 底部输入区 */}
        <div className="flex-shrink-0 px-6 py-4" style={{ background: 'var(--bg)' }}>
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </div>

      {/* 右侧 Agent 面板 */}
      {agentSteps.length > 0 && (
        <div className="agent-panel hidden xl:block">
          <AgentPanel steps={agentSteps} loading={loading} />
        </div>
      )}
    </div>
  )
}
