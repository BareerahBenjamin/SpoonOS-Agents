import { useState } from 'react'
import { Activity, AlertTriangle, ArrowUpRight, BarChart3, BookOpen, CircleHelp, ExternalLink, FileText, LineChart, Send } from 'lucide-react'
import { date, explain, money, number, post, reportLabels, sourceLabels, sourceName, type Answer, type Evidence, type Report, type ReportStatus, type Source } from './api'

const shortDate = new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', timeZone: 'UTC' })
const directions: Record<string, string> = { BUY: '买入', HOLD: '持有', SELL: '卖出' }

export function ReportBadge({ status }: { status: ReportStatus }) {
  return <span className={`badge tone-${status}`}>{reportLabels[status]}</span>
}

function SourceNote({ source }: { source?: Source }) {
  if (!source) return null
  return <p className="source-note">
    <span>{sourceName(source.source)}</span>
    {source.updated_at && <span>更新 {date(source.updated_at)}</span>}
    {source.fetched_at && <span>采集 {date(source.fetched_at)}</span>}
  </p>
}

function safeLink(value?: string) {
  try {
    const url = new URL(value ?? '')
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : undefined
  } catch { return undefined }
}

function Citations({ ids }: { ids: string[] }) {
  return <span className="citations" aria-label="引用的证据">{ids.map((id) => (
    <a key={id} href={`#evidence-${id}`} onClick={(event) => {
      event.preventDefault()
      document.getElementById(`evidence-${id}`)?.focus()
    }}>{id}</a>
  ))}</span>
}

function EvidenceItem({ item }: { item: Evidence }) {
  const title = item.title ?? ({ price: '市场行情快照', history: '每日历史价格' } as Record<string, string>)[item.id] ?? item.id
  const link = safeLink(item.url)
  return <li className="evidence-item" id={`evidence-${item.id}`} tabIndex={-1}>
    <div className="evidence-head">
      <span className="badge code">{item.id}</span>
      <strong>{link ? <a href={link} target="_blank" rel="noopener noreferrer">{title} <ExternalLink size={13} aria-label="在新标签页打开" /></a> : title}</strong>
    </div>
    {item.content && <p>{item.content}</p>}
    <p className="source-note">
      <span>{sourceName(item.source)}</span>
      {item.id.startsWith('news-') && <span>发布 {date(item.published_at)}</span>}
      {item.updated_at && <span>更新 {date(item.updated_at)}</span>}
      {item.fetched_at && <span>采集 {date(item.fetched_at)}</span>}
    </p>
  </li>
}

function MarketChart({ history }: { history: Report['data']['history_data'] }) {
  const [recent, setRecent] = useState(false)
  const valid = history?.status === 'live' ? (history.prices ?? []).filter(([t, p]) => Number.isFinite(t) && Number.isFinite(p) && p > 0) : []
  const points = recent ? valid.slice(-30) : valid
  if (points.length < 2) return <div className="empty compact"><LineChart size={24} /><strong>没有可绘制的历史价格</strong><span>{history?.source === 'demo' ? '演示模式未提供历史样本。' : '当前快照没有足够的有效历史样本。'}</span></div>
  const [first] = points
  const last = points[points.length - 1]
  const prices = points.map(([, price]) => price)
  const low = Math.min(...prices)
  const high = Math.max(...prices)
  const range = high - low
  const width = 600
  const height = 140
  const line = points.map(([stamp, price]) => [
    ((stamp - first[0]) / (last[0] - first[0] || 1) * width).toFixed(1),
    (range ? 6 + (1 - (price - low) / range) * (height - 12) : height / 2).toFixed(1),
  ].join(',')).join(' ')
  return <>
    {valid.length > 30 && <div className="chart-toolbar"><span>{points.length} 个日度样本 · USD</span><div className="segment" aria-label="价格时间范围">
      <button type="button" aria-pressed={recent} onClick={() => setRecent(true)}>近 30 个</button>
      <button type="button" aria-pressed={!recent} onClick={() => setRecent(false)}>全部</button>
    </div></div>}
    <div className="chart">
      <div className="chart-y" aria-hidden="true"><span>{money(high, true)}</span><span>{money(low + range / 2, true)}</span><span>{money(low, true)}</span></div>
      <svg role="img" aria-label={`从 ${shortDate.format(first[0])} 到 ${shortDate.format(last[0])} 的 ${points.length} 个价格样本，最低 ${money(low)}，最高 ${money(high)}`} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        {[6, height / 2, height - 6].map((y) => <line key={y} x1="0" x2={width} y1={y} y2={y} vectorEffect="non-scaling-stroke" />)}
        <polygon points={`0,${height} ${line} ${width},${height}`} />
        <polyline points={line} vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="chart-x"><span>{shortDate.format(first[0])}</span><span>{shortDate.format(last[0])}</span></div>
    </div>
    <SourceNote source={history} />
  </>
}

export function QuestionBox({ report }: { report?: Report }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<Answer>()
  const [asked, setAsked] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  return <form className="question-form" onSubmit={async (event) => {
    event.preventDefault()
    const input = question.trim()
    if (!input || busy) return
    setBusy(true); setError(''); setAnswer(undefined); setAsked(input)
    try {
      setAnswer(await post<Answer>(report ? `/research/${report.run_id}/questions` : '/questions', { question: input }))
    } catch (error) { setError(explain(error)) }
    finally { setBusy(false) }
  }}>
    <label htmlFor="question-text">{report ? '你想了解这份报告的什么？' : '你的问题'}</label>
    <textarea id="question-text" value={question} onChange={(event) => setQuestion(event.target.value)} required maxLength={10000} rows={3}
      placeholder={report ? '例如：这个结论引用了哪些证据？' : '例如：以太坊的最新行情和历史走势如何？'} />
    <div className="form-actions"><button className="button primary" disabled={busy || !question.trim()} type="submit">{busy ? '正在获取回答' : '提交问题'} <Send size={15} /></button></div>
    <div role="status">{busy ? <p className="subtle">SpoonOS 正在处理你的问题。</p> : answer && <span className="visually-hidden">回答已生成。</span>}</div>
    {error && <p className="notice danger" role="alert">{error}</p>}
    {answer && <div className="answer" tabIndex={0}><strong>{asked}</strong><p>{answer.answer}</p>{answer.evidence_ids && <Citations ids={answer.evidence_ids} />}</div>}
  </form>
}

function limitation(value: string) {
  const known: Record<string, string> = {
    'price: mock': '行情使用固定演示值。',
    'history: Demo history is not provided': '演示模式不提供历史价格。',
    'news: mock': '新闻使用演示数据，不可用作证据。',
    'Demo data cannot support an investment conclusion': '演示数据不可用于得出投资结论。',
    'news: TAVILY_API_KEY is not configured': '未配置 Tavily 密钥，无法检索新闻。',
    'indicators: historical samples are insufficient or invalid': '历史样本不足或无效，无法计算部分指标。',
    '24h price change is unavailable; rule signal omitted': '没有有效的 24 小时涨跌幅，未生成规则信号。',
    'Some news publication dates are unknown; recency is unverified': '部分新闻未提供发布时间，无法判断时效。',
  }
  return known[value] ?? value
}

export function ReportContent({ report }: { report: Report }) {
  const { price_data: price, history_data: history, technical_indicators: indicators, sentiment_data: news } = report.data
  const change = price?.price_change_percentage_24h
  const model = report.model_report
  return <div className="report-stack">
    {report.status === 'demo' && <p className="notice warning"><AlertTriangle size={17} />这是一份演示报告。下方行情为固定示例值，未调用模型生成结论。</p>}
    <section className="panel" aria-labelledby="quote-title">
      <div className="panel-heading"><h2 id="quote-title"><BarChart3 />行情快照</h2><span className="badge neutral">{sourceName(price?.status)}</span></div>
      <dl className="metrics">
        <div><dt>价格（USD）</dt><dd>{money(price?.current_price)}</dd></div>
        <div><dt>24 小时涨跌</dt><dd className={typeof change === 'number' ? change > 0 ? 'up' : change < 0 ? 'down' : '' : ''}>{typeof change === 'number' ? `${change > 0 ? '+' : ''}${number(change)}%` : '—'}</dd></div>
        <div><dt>市值</dt><dd>{money(price?.market_cap, true)}</dd></div>
        <div><dt>24 小时成交量</dt><dd>{money(price?.total_volume, true)}</dd></div>
      </dl>
      <SourceNote source={price} />
    </section>
    <section className="panel" aria-labelledby="chart-title">
      <div className="panel-heading"><h2 id="chart-title"><LineChart />历史价格</h2></div>
      <MarketChart history={history} />
    </section>
    <section className="panel" aria-labelledby="indicator-title">
      <div className="panel-heading"><h2 id="indicator-title"><Activity />技术指标</h2>{indicators?.sample_count && <span className="badge neutral">{indicators.sample_count} 个日度样本</span>}</div>
      {indicators?.status === 'live'
        ? <dl className="metrics">
            <div><dt>RSI (14)</dt><dd>{number(indicators.rsi)}</dd></div>
            <div><dt>MACD (12, 26, 9)</dt><dd>{number(indicators.macd?.macd_line, 4)}</dd></div>
            <div><dt>MACD 信号线</dt><dd>{number(indicators.macd?.signal_line, 4)}</dd></div>
            <div><dt>MACD 柱线</dt><dd>{number(indicators.macd?.histogram, 4)}</dd></div>
            <div><dt>SMA (7)</dt><dd>{money(indicators.moving_averages?.ma_7)}</dd></div>
            <div><dt>SMA (25)</dt><dd>{money(indicators.moving_averages?.ma_25)}</dd></div>
            <div><dt>SMA (99)</dt><dd>{money(indicators.moving_averages?.ma_99)}</dd></div>
          </dl>
        : <p className="subtle">历史价格样本不足，未计算技术指标。</p>}
    </section>
    <section className="panel" aria-labelledby="conclusion-title">
      <div className="panel-heading"><h2 id="conclusion-title"><FileText />研究结论</h2></div>
      <div className="compare">
        <div><span>模型结论</span><strong>{directions[report.recommendation ?? ''] ?? '未生成'}</strong><small>{model ? `${report.provider} / ${report.model}` : '没有通过校验的模型报告'}</small></div>
        <div><span>24 小时规则信号</span><strong>{directions[report.rule_signal ?? ''] ?? '未生成'}</strong><small>依据 24 小时涨跌幅阈值</small></div>
      </div>
      {report.disagreement && <p className="notice warning"><AlertTriangle size={16} />模型结论与规则信号不同，可对照下方理由和证据。</p>}
      {model && <div className="report-prose"><h3>{model.summary}</h3><p>{model.reasoning}</p><Citations ids={model.evidence_ids} /></div>}
      {!!report.limitations.length && <div className="limitations"><h3>数据限制</h3><ul>{report.limitations.map((item, i) => <li key={i}>{limitation(item)}</li>)}</ul></div>}
    </section>
    <section className="panel" aria-labelledby="evidence-title">
      <div className="panel-heading"><h2 id="evidence-title"><BookOpen />证据索引</h2><span className="badge neutral">{report.evidence.length} 条</span></div>
      {report.evidence.length ? <ul className="evidence-list">{report.evidence.map((item) => <EvidenceItem key={item.id} item={item} />)}</ul> : <p className="subtle">这份快照没有可引用的真实证据。</p>}
      {news && <p className="source-note"><span>新闻：{sourceLabels[news.status ?? ''] ?? '未记录'}</span></p>}
    </section>
    <section className="panel" aria-labelledby="followup-title">
      <div className="panel-heading"><h2 id="followup-title"><CircleHelp />基于快照追问</h2>{model && <span className="badge neutral"><ArrowUpRight size={13} />引用可追溯</span>}</div>
      {model ? <><p className="subtle">SpoonOS 只使用当前保存的报告和证据作答。</p><QuestionBox report={report} /></> : <p className="subtle">这份快照没有通过校验的模型结论，暂不能追问。</p>}
    </section>
  </div>
}
