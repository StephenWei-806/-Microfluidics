/**
 * 内容段类型定义
 * 用于 MessageBubble 组件中区分文本段落和 mermaid 图表段落
 */
export interface ContentSegment {
  type: 'text' | 'mermaid'
  content: string        // 原始内容
  rendered?: string      // 渲染后的 HTML/SVG
  id?: string           // mermaid 块的唯一 ID
  renderError?: boolean  // 渲染是否失败
}
