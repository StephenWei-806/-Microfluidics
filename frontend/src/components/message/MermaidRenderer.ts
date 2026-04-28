import mermaid from 'mermaid'
import hljs from 'highlight.js'
import { hashContent, escapeHtml } from './ContentParser'
import type { ContentSegment } from './types'

// mermaid 代码块计数器，用于生成唯一 ID
let mermaidCounter = 0

// 初始化 mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    htmlLabels: true,
    useMaxWidth: true,
  },
})

// 预处理 mermaid 代码，统一为节点标签添加引号以兼容 v11 严格语法
export function sanitizeMermaidCode(code: string): string {
  let sanitized = code

  // === 预处理：清理AI生成的异常语法 ===

  // Pattern: (("[#quot;text#quot;]")) 或 (("(#quot;text#quot;")) → (("text"))
  sanitized = sanitized.replace(
    /\(\(\s*"?[\[\(]?#quot;([^#]*?)#quot;[\]\)]?"?\s*\)\)/g,
    '(("$1"))'
  )

  // 移除不完整的style声明（如截断的 'styl'）
  sanitized = sanitized.replace(/^\s*styl\b(?!e\b).*$/gm, '')

  // 去重重复的 style 声明
  const seenStyles = new Set<string>()
  sanitized = sanitized.split('\n').filter(line => {
    const trimmed = line.trim()
    if (trimmed.startsWith('style ')) {
      if (seenStyles.has(trimmed)) return false
      seenStyles.add(trimmed)
    }
    return true
  }).join('\n')

  // 压缩连续空行
  sanitized = sanitized.replace(/\n{3,}/g, '\n\n')

  // === 以下为原有的节点标签引号兼容处理 ===

  // 处理 ((...)) 双圆括号（圆形节点）
  sanitized = sanitized.replace(
    /([a-zA-Z_]\w*)\(\(([^)]*)\)\)/g,
    (_match, id, label) => {
      const trimmed = label.trim()
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) return _match
      return `${id}(("${label.replace(/"/g, '#quot;')}"))`
    }
  )

  // 处理 (...) 单圆括号（圆角节点）— 排除已处理的双圆括号
  sanitized = sanitized.replace(
    /([a-zA-Z_]\w*)\(([^("][^)]*)\)/g,
    (_match, id, label) => {
      const trimmed = label.trim()
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) return _match
      // 跳过纯英文字母数字标签（mermaid 原生支持）
      if (/^[a-zA-Z0-9_]+$/.test(trimmed)) return _match
      return `${id}("${label.replace(/"/g, '#quot;')}")`
    }
  )

  // 处理 [...] 方括号（矩形节点）
  sanitized = sanitized.replace(
    /([a-zA-Z_]\w*)\[([^\]]*)\]/g,
    (_match, id, label) => {
      const trimmed = label.trim()
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) return _match
      if (/^[a-zA-Z0-9_]+$/.test(trimmed)) return _match
      return `${id}["${label.replace(/"/g, '#quot;')}"]`
    }
  )

  // 处理 {...} 菱形节点（决策框）
  sanitized = sanitized.replace(
    /([a-zA-Z_]\w*)\{([^}]*)\}/g,
    (_match, id, label) => {
      const trimmed = label.trim()
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) return _match
      if (/^[a-zA-Z0-9_]+$/.test(trimmed)) return _match
      return `${id}{"${label.replace(/"/g, '#quot;')}"}`
    }
  )

  return sanitized
}

// 带超时的 mermaid 渲染辅助函数
function renderWithTimeout(renderId: string, code: string, timeoutMs = 10000): Promise<{ svg: string }> {
  return Promise.race([
    mermaid.render(renderId, code),
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error(`Mermaid 渲染超时 (${timeoutMs}ms)`)), timeoutMs)
    )
  ])
}

// 渲染单个 mermaid 段落
export async function renderMermaidSegment(
  segment: ContentSegment,
  renderedHashes: Set<string>
): Promise<void> {
  if (segment.type !== 'mermaid' || segment.rendered) return

  const contentHash = hashContent(segment.content)
  if (renderedHashes.has(contentHash)) return

  // 提前注册 hash，防止并发重复渲染
  renderedHashes.add(contentHash)

  const id = `mermaid-${Date.now()}-${mermaidCounter++}`
  segment.id = id

  // 预处理 mermaid 代码
  const sanitizedCode = sanitizeMermaidCode(segment.content)
  const codeChanged = sanitizedCode !== segment.content

  try {
    const { svg } = await renderWithTimeout(id, sanitizedCode)
    segment.rendered = svg
    segment.renderError = false  // 确保显式设置成功状态
  } catch {
    // 清理 mermaid 可能留下的临时 DOM 元素
    const errorElement = document.getElementById(id)
    if (errorElement) {
      errorElement.remove()
    }

    // 如果净化后仍然失败，尝试用原始代码（以防净化反而破坏了正确语法）
    if (codeChanged) {
      const retryId = `mermaid-${Date.now()}-${mermaidCounter++}`
      segment.id = retryId
      try {
        const { svg } = await renderWithTimeout(retryId, segment.content)
        segment.rendered = svg
        segment.renderError = false  // 确保显式设置成功状态
        return
      } catch {
        // 清理重试时可能留下的临时 DOM 元素
        const retryErrorElement = document.getElementById(retryId)
        if (retryErrorElement) {
          retryErrorElement.remove()
        }
      }
    }

    segment.renderError = true
    // 降级为高亮源码，优先使用净化后的代码
    const codeToDisplay = codeChanged ? sanitizedCode : segment.content
    try {
      const highlighted = hljs.highlight(codeToDisplay, { language: 'plaintext' }).value
      segment.rendered = highlighted
    } catch {
      // 高亮处理也失败，使用纯HTML转义保底
      segment.rendered = escapeHtml(codeToDisplay)
    }
    // 注意：降级显示也是有效结果，不移除 hash，避免无限重试
  }
}

// 渲染所有未渲染的 mermaid 段落（顺序执行，避免并发问题）
export async function renderAllMermaidSegments(
  segments: ContentSegment[],
  renderedHashes: Set<string>
): Promise<void> {
  const mermaidSegments = segments.filter(s => s.type === 'mermaid' && !s.rendered)
  for (const seg of mermaidSegments) {
    await renderMermaidSegment(seg, renderedHashes)
  }
}

// 为mermaid容器添加事件监听（限定在当前组件范围内）
export function addMermaidEventListeners(
  containerRef: HTMLElement | undefined,
  callbacks: {
    onClick: (svgHtml: string) => void
    onContextMenu: (event: MouseEvent, svgElement: HTMLElement) => void
  },
  cleanupFunctions: (() => void)[]
): void {
  // 先清理旧的事件监听器（只清理 mermaid container 相关的监听器，不触碰 document click）
  cleanupFunctions.forEach(fn => fn())
  cleanupFunctions.length = 0

  // 限定在当前消息内容容器内查找
  const containers = containerRef?.querySelectorAll<HTMLElement>('.mermaid-container') ?? []
  containers.forEach((container) => {
    const svg = container.querySelector('svg')
    if (!svg) return

    // 添加点击事件
    const handleClick = () => {
      callbacks.onClick(svg.outerHTML)
    }
    container.addEventListener('click', handleClick)
    container.style.cursor = 'pointer'

    // 添加右键事件
    const handleContextMenu = (e: MouseEvent) => {
      callbacks.onContextMenu(e, svg as unknown as HTMLElement)
    }
    container.addEventListener('contextmenu', handleContextMenu)

    // 存储清理函数
    cleanupFunctions.push(() => {
      container.removeEventListener('click', handleClick)
      container.removeEventListener('contextmenu', handleContextMenu)
      container.style.cursor = ''
    })
  })
}
