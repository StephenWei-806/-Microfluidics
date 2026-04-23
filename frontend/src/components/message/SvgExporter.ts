import { ElMessage } from 'element-plus'

// 将SVG转换为Canvas
export async function svgToCanvas(svgElement: HTMLElement): Promise<HTMLCanvasElement> {
  // 克隆 SVG 以避免修改原始 DOM
  const clonedSvg = svgElement.cloneNode(true) as SVGSVGElement

  // 确保有 xmlns 属性
  if (!clonedSvg.getAttribute('xmlns')) {
    clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  }
  // 确保 xlink namespace
  if (!clonedSvg.getAttribute('xmlns:xlink')) {
    clonedSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  }

  // 获取实际尺寸
  const svgRect = svgElement.getBoundingClientRect()
  const width = svgRect.width || parseInt(clonedSvg.getAttribute('width') || '800')
  const height = svgRect.height || parseInt(clonedSvg.getAttribute('height') || '600')

  // 设置显式宽高
  clonedSvg.setAttribute('width', String(width))
  clonedSvg.setAttribute('height', String(height))

  // 收集并内联计算样式（将所有相关 CSS 嵌入 SVG）
  const styleElement = document.createElement('style')
  const cssRules: string[] = []
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        cssRules.push(rule.cssText)
      }
    } catch {
      // 跨域样式表会抛出错误，忽略即可
    }
  }
  styleElement.textContent = cssRules.join('\n')
  clonedSvg.insertBefore(styleElement, clonedSvg.firstChild)

  // 使用 data URL 方式，比 Blob URL 更可靠
  const svgData = new XMLSerializer().serializeToString(clonedSvg)
  const svgDataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData)

  // 计算满足最小分辨率要求的缩放因子
  const MIN_LONG_SIDE = 1920
  const MIN_SHORT_SIDE = 720

  let targetWidth: number
  let targetHeight: number

  if (width >= height) {
    // 横向图表
    targetWidth = Math.max(MIN_LONG_SIDE, width)
    targetHeight = targetWidth * (height / width)
    if (targetHeight < MIN_SHORT_SIDE) {
      targetHeight = MIN_SHORT_SIDE
      targetWidth = targetHeight * (width / height)
    }
  } else {
    // 纵向图表
    targetHeight = Math.max(MIN_LONG_SIDE, height)
    targetWidth = targetHeight * (width / height)
    if (targetWidth < MIN_SHORT_SIDE) {
      targetWidth = MIN_SHORT_SIDE
      targetHeight = targetWidth * (height / width)
    }
  }

  const scale = Math.max(2, targetWidth / width, targetHeight / height)

  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('无法获取 canvas 上下文'))
        return
      }

      // 填充白色背景
      ctx.fillStyle = 'white'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve(canvas)
    }
    img.onerror = () => {
      reject(new Error('SVG 图片加载失败'))
    }
    img.src = svgDataUrl
  })
}

// 复制图表到剪贴板
export async function copyChart(svgElement: HTMLElement | null, onComplete?: () => void): Promise<void> {
  if (!svgElement) return

  try {
    const canvas = await svgToCanvas(svgElement)
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => {
        if (b) {
          resolve(b)
        } else {
          reject(new Error('Canvas toBlob 返回空'))
        }
      }, 'image/png')
    })

    // 检查是否支持 ClipboardItem API
    if (typeof ClipboardItem !== 'undefined') {
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob })
      ])
      ElMessage.success('图表已复制到剪贴板')
    } else {
      ElMessage.warning('当前浏览器不支持复制图片，请使用下载功能')
    }
  } catch {
    ElMessage.error('复制失败，请使用下载功能')
  } finally {
    onComplete?.()
  }
}

// 下载图表为PNG
export async function downloadChart(svgElement: HTMLElement | null, onComplete?: () => void): Promise<void> {
  if (!svgElement) return

  try {
    const canvas = await svgToCanvas(svgElement)
    const dataUrl = canvas.toDataURL('image/png')

    const link = document.createElement('a')
    link.href = dataUrl
    link.download = 'mermaid-chart.png'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('图表已下载')
  } catch {
    ElMessage.error('下载失败')
  } finally {
    onComplete?.()
  }
}
