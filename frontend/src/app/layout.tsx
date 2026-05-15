import type { Metadata } from 'next'
import { AntdRegistry } from '@ant-design/nextjs-registry'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import './globals.css'

export const metadata: Metadata = {
  title: 'DeepScribe - 个人知识库深度研究助手',
  description: '基于 RAG + AI Agent 的智能知识管理平台',
}

const theme = {
  token: {
    colorPrimary: '#0052d9',
    borderRadius: 8,
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen">
        <AntdRegistry>
          <ConfigProvider theme={theme} locale={zhCN}>
            {children}
          </ConfigProvider>
        </AntdRegistry>
      </body>
    </html>
  )
}
