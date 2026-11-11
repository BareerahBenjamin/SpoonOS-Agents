export type ReportStatus = 'completed' | 'partial' | 'unavailable' | 'failed' | 'demo'
export type RunState = 'queued' | 'running' | 'finished' | 'failed'

export interface Run {
  run_id: string
  symbol: string
  demo_mode: boolean
  state: RunState
  created_at: string
  updated_at: string
  cursor: number
  report_status: ReportStatus | null
  error: string | null
}

export interface Step {
  node: string
  phase?: 'started' | 'finished'
  status?: string
  duration_ms?: number
  finished_at?: string
  at?: string
}

export interface Source {
  source?: string
  status?: string
  fetched_at?: string | null
  updated_at?: string | null
  error?: string | null
}

export interface Evidence extends Source {
  id: string
  title?: string
  url?: string
  content?: string
  published_at?: string | null
}

export interface ReportRow {
  run_id: string
  created_at: string
  symbol: string
  status: ReportStatus
  provider: string
  model: string
  version: number
}

export interface Report extends ReportRow {
  snapshot_id: string
  recommendation: string | null
  rule_signal: string | null
  disagreement: boolean
  limitations: string[]
  evidence: Evidence[]
  events: Step[]
  model_report: { summary: string; reasoning: string; evidence_ids: string[] } | null
  data: {
    price_data?: Source & {
      current_price?: number | null
      price_change_percentage_24h?: number | null
      market_cap?: number | null
      total_volume?: number | null
    }
    history_data?: Source & { prices?: [number, number][]; days?: number }
    technical_indicators?: Source & {
      rsi?: number | null
      macd?: { macd_line?: number; signal_line?: number; histogram?: number } | null
      moving_averages?: { ma_7?: number | null; ma_25?: number | null; ma_99?: number | null }
      sample_count?: number
    }
    sentiment_data?: Source
  }
}

export interface Settings {
  demo_mode: boolean
  model: { provider: string; name: string; configured: boolean }
  coingecko: { plan: string }
  tavily: { configured: boolean }
}
export interface Health { status: string; sdk: string; sdk_version: string }
export interface Answer { answer: string; evidence_ids?: string[] }

export class ApiError extends Error {
  constructor(public status: number, detail: string) { super(detail) }
}

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, options)
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, typeof body?.detail === 'string' ? body.detail : '')
  if (body === null) throw new Error('服务返回了无效响应')
  return body as T
}

export function post<T>(path: string, body: object): Promise<T> {
  return api<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
}

export function explain(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return '找不到这项研究或报告。'
    if (error.status === 422) return '输入格式有误，请检查后重试。'
    if (error.status === 429) return '研究队列已满，请稍后重试。'
    if (error.status === 409) return '这份快照没有通过校验的模型结论，无法追问。'
    if (error.status === 503) return /_API_KEY/.test(error.message)
      ? '模型密钥尚未配置。可在设置中开启演示模式，或补齐服务端配置。'
      : '服务配置无效，请检查后端环境变量。'
    if (error.status === 502) return '模型请求未完成或结果未通过校验，请稍后重试。'
    return '服务暂时无法处理这项请求。'
  }
  return '无法连接到研究服务，请检查服务是否已启动。'
}

export const reportLabels: Record<ReportStatus, string> = {
  completed: '已完成', partial: '部分可用', unavailable: '数据不可用', failed: '生成失败', demo: '演示',
}

export const sourceLabels: Record<string, string> = {
  live: '已取得', completed: '已完成', partial: '部分可用', unavailable: '不可用',
  failed: '失败', demo: '演示数据', mock: '演示数据', coingecko: 'CoinGecko', tavily: 'Tavily',
}

export const steps = [
  { id: 'collect_price', name: '获取市场行情', detail: 'CoinGecko · 价格与成交量' },
  { id: 'collect_history', name: '拉取历史价格', detail: 'CoinGecko · 每日收盘价' },
  { id: 'collect_news', name: '检索新闻证据', detail: 'Tavily · 标题与来源' },
  { id: 'calculate_indicators', name: '计算技术指标', detail: 'RSI · MACD · SMA' },
  { id: 'data_quality', name: '检查数据质量', detail: '核对来源、时间与完整性' },
  { id: 'generate_report', name: '生成研究报告', detail: 'SpoonOS · 校验结论与引用' },
]

export function date(value?: string | null): string {
  const stamp = value ? new Date(value) : null
  return stamp && !Number.isNaN(stamp.getTime())
    ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short', hour12: false }).format(stamp)
    : '未知'
}

export function number(value?: number | null, digits = 2, compact = false): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? new Intl.NumberFormat('en-US', { maximumFractionDigits: digits, notation: compact ? 'compact' : 'standard' }).format(value)
    : '—'
}

export function money(value?: number | null, compact = false): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return '$' + number(value, Math.abs(value) < 1 ? 8 : 2, compact)
}

export function sourceName(source?: string): string {
  return source ? (sourceLabels[source] ?? source) : '未记录'
}
