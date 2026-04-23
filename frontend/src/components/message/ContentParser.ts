import { marked } from 'marked'
import type { ContentSegment } from './types'

// HTML特殊字符转义
export function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }
  return text.replace(/[&<>"']/g, char => map[char])
}

// 计算内容的简单 hash，用于去重
export function hashContent(content: string): string {
  // 对 content 做 trim 后再计算 hash，避免流式传输中末尾空白变化导致 hash 不同
  const trimmed = content.trim()
  let hash = 0
  for (let i = 0; i < trimmed.length; i++) {
    const char = trimmed.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  return hash.toString(36)
}

// 解析内容，拆分为 text 和 mermaid 段落
export function parseContent(content: string): { 
  segments: ContentSegment[] 
  hasUnclosedMermaid: boolean 
  trailingText: string 
} {
  const segments: ContentSegment[] = []
  // 闭合的 mermaid 代码块（更宽松的正则，兼容空格和大小写变体）
  const mermaidRegex = /```\s*mermaid[ \t]*\r?\n([\s\S]*?)```/gi
  let lastIndex = 0
  let match

  while ((match = mermaidRegex.exec(content)) !== null) {
    // 添加 mermaid 之前的文本
    if (match.index > lastIndex) {
      const textContent = content.slice(lastIndex, match.index)
      if (textContent.trim()) {
        segments.push({
          type: 'text',
          content: textContent,
          rendered: marked(textContent) as string
        })
      }
    }
    
    // 添加 mermaid 代码块
    const mermaidCode = match[1].trim()
    if (mermaidCode) {
      segments.push({
        type: 'mermaid',
        content: mermaidCode,
        rendered: undefined,    // 初始化 rendered 属性，确保 Vue 响应式追踪
        renderError: false
      })
    }
    
    lastIndex = match.index + match[0].length
  }

  // 检查末尾是否有未闭合的 mermaid 块
  const remainingText = content.slice(lastIndex)
  // 未闭合的 mermaid 代码块（更宽松的正则）
  const unclosedMermaidMatch = remainingText.match(/```\s*mermaid[ \t]*\r?\n?([\s\S]*)$/i)
  
  if (unclosedMermaidMatch) {
    // 有未闭合的 mermaid，前面的文本先处理
    const beforeMermaid = remainingText.slice(0, unclosedMermaidMatch.index)
    if (beforeMermaid.trim()) {
      segments.push({
        type: 'text',
        content: beforeMermaid,
        rendered: marked(beforeMermaid) as string
      })
    }
    return {
      segments,
      hasUnclosedMermaid: true,
      trailingText: remainingText.slice(unclosedMermaidMatch.index)
    }
  }

  // 没有未闭合的 mermaid，剩余部分作为普通文本
  if (remainingText.trim()) {
    segments.push({
      type: 'text',
      content: remainingText,
      rendered: marked(remainingText) as string
    })
  }

  return {
    segments,
    hasUnclosedMermaid: false,
    trailingText: ''
  }
}
