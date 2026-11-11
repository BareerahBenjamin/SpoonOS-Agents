import { StrictMode, useCallback, useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity, ArrowLeft, ArrowRight, ArrowUpRight, ChartNoAxesCombined, Check, ChevronRight,
  CircleAlert, CircleHelp, Clock3, Database, FlaskConical, History, LayoutDashboard, Newspaper, Plus, RefreshCw,
  Search, Settings2, Workflow,
} from 'lucide-react'
import { api, date, explain, post, reportLabels, sourceLabels, steps, type Health, type Report, type ReportRow, type ReportStatus, type Run, type Settings, type Step } from './api'
import { QuestionBox, ReportBadge, ReportContent } from './report'
import { useResearch } from './use-research'
import './styles.css'

const assets = [
  { symbol: 'BTC', name: 'Bitcoin' }, { symbol: 'ETH', name: 'Ethereum' },
  { symbol: 'SOL', name: 'Solana' }, { symbol: 'BNB', name: 'BNB' },
]
const uuid = /^[\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12}$/i
const validAsset = /^[A-Za-z0-9-]{1,64}$/
const coverImage = new URL('./assets/research-cover.jpg', import.meta.url).href
const navigation = [
  { id: 'workbench', label: '研究工作台', icon: LayoutDashboard },
  { id: 'history', label: '研究记录', icon: History },
  { id: 'question', label: '快速问答', icon: CircleHelp },
  { id: 'settings', label: '设置', icon: Settings2 },
] as const
type Page = typeof navigation[number]['id']
type Mode = 'server' | 'live' | 'demo'

function route() {
  const value = window.location.hash.slice(1)
  const candidate = value.startsWith('run/') ? value.slice(4) : ''
  const asset = value.startsWith('workbench/') ? value.slice(10) : ''
  const page = navigation.find((item) => item.id === value)?.id ?? 'workbench'
  return { page, id: uuid.test(candidate) ? candidate.toLowerCase() : '', asset: validAsset.test(asset) ? asset : '' }
}

function readMode(): Mode {
  try {
    const saved = window.localStorage.getItem('spoonos-research-mode')
    if (saved === 'live' || saved === 'demo') return saved
  } catch { /* A disabled storage preference lasts for the current page. */ }
  return 'server'
}

function BrandRail({ health }: { health?: Health }) {
  return <div className="brand-rail">
    <a className="rail-brand" href="#workbench" aria-label="SpoonOS 首页">
      <span className="rail-square" aria-hidden="true" />
      <strong>SpoonOS</strong>
    </a>
    {health && <span className="rail-sdk">SDK {health.sdk_version}</span>}
  </div>
}

function Navigation({ page }: { page: Page }) {
  return <nav className="masthead-nav" aria-label="工作空间">
    {navigation.map(({ id, label, icon: Icon }) => (
      <a key={id} href={`#${id}`} aria-current={page === id ? 'page' : undefined}>
        <Icon size={15} aria-hidden="true" />{label}
      </a>
    ))}
  </nav>
}

function SectionTitle({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="page-title">
    <div><h1>{title}</h1><p>{description}</p></div>
    {action}
  </div>
}

function StatusDot({ tone }: { tone: string }) {
  return <span className={`status-dot ${tone}`} aria-hidden="true" />
}

function Execution({ run, report, events, connection, selected }: { run?: Run; report?: Report; events: Record<string, Step>; connection: string; selected: boolean }) {
  const stored = Object.fromEntries((report?.events ?? []).map((item) => [item.node, item]))
  const terminal = !!report || run?.state === 'failed' || run?.state === 'finished'
  const summary = run?.state === 'queued' ? '正在排队' : run?.state === 'running' ? '研究进行中' :
    run?.state === 'failed' ? '运行中断' : terminal ? '流程已结束' : selected ? '等待连接' : '尚未开始'
  const count = steps.filter(({ id }) => stored[id] || events[id]?.phase === 'finished').length
  return <section className="panel execution" aria-labelledby="execution-title" id="execution-log" tabIndex={-1}>
    <div className="panel-heading"><h2 id="execution-title"><Activity />执行日志</h2><span className="execution-count">{count}/{steps.length}</span></div>
    <div className="execution-state" role="status"><StatusDot tone={run?.state === 'running' || terminal ? run?.state === 'failed' ? 'red' : 'green' : 'muted'} />{summary}
      {!terminal && connection === 'retrying' && <span className="retry-label">连接中断，正在重连</span>}
      {run?.state === 'running' && connection === 'live' && <span className="retry-label">实时更新</span>}
    </div>
    <ol className="timeline">
      {steps.map(({ id, name, detail }) => {
        const entry = stored[id] ?? events[id]
        const running = entry?.phase === 'started' && !terminal
        const ended = entry && entry.phase !== 'started'
        const skipped = terminal && !ended
        const tone = running ? 'active' : ended ? ['failed', 'unavailable', 'partial', 'demo', 'mock'].includes(entry.status ?? '') ? 'warning' : 'done' : 'pending'
        const label = running ? '进行中' : ended ? sourceLabels[entry.status ?? ''] ?? '已结束' : skipped ? entry ? '已中断' : '未执行' : '等待'
        return <li key={id} className={tone}>
          <span className="step-index" aria-hidden="true">{tone === 'done' ? <Check size={13} /> : tone === 'warning' ? <CircleAlert size={13} /> : <Clock3 size={13} />}</span>
          <div className="step-copy"><strong>{name}</strong><small>{detail}</small></div>
          <div className="step-result"><span>{label}</span>{ended && typeof entry.duration_ms === 'number' && <small>{entry.duration_ms < 1000 ? `${Math.round(entry.duration_ms)} ms` : `${(entry.duration_ms / 1000).toFixed(1)} s`}</small>}</div>
        </li>
      })}
    </ol>
  </section>
}

function Sources({ settings, mode }: { settings?: Settings; mode: Mode }) {
  const demo = mode === 'demo' || (mode === 'server' && settings?.demo_mode)
  return <section className="panel sources" aria-labelledby="sources-title">
    <div className="panel-heading"><h2 id="sources-title"><Database />数据与模型</h2><a href="#settings" className="text-link">设置 <ChevronRight size={14} /></a></div>
    <ul>
      <li><ChartNoAxesCombined size={16} /><div><strong>CoinGecko</strong><small>行情与历史价格</small></div><span>{settings ? demo ? '演示' : settings.coingecko.plan === 'pro' ? 'Pro API' : '公开 API' : '未知'}</span></li>
      <li><Newspaper size={16} /><div><strong>Tavily</strong><small>新闻证据</small></div><span>{settings ? demo ? '演示' : settings.tavily.configured ? '已配置' : '未配置' : '未知'}</span></li>
      <li><Workflow size={16} /><div><strong>SpoonOS</strong><small>编排与模型</small></div><span>{settings ? demo ? '演示' : settings.model.configured ? '已配置' : '未配置' : '未知'}</span></li>
    </ul>
  </section>
}

function HistoryRows({ rows, loading, error, onRetry, filtered = false, showModel = false }: { rows: ReportRow[]; loading: boolean; error: string; onRetry: () => void; filtered?: boolean; showModel?: boolean }) {
  if (loading && !rows.length) return <p className="empty compact" role="status">正在读取研究记录…</p>
  if (error) return <div className="empty compact"><CircleAlert size={24} /><p role="alert">{error}</p><button className="button secondary" type="button" onClick={onRetry}>重新加载</button></div>
  if (!rows.length) return <div className="empty compact"><History size={25} /><strong>{filtered ? '没有符合筛选条件的报告' : '还没有研究报告'}</strong><span>{filtered ? '可更换资产或报告状态。' : '完成的研究会自动保存在这里。'}</span></div>
  return <ul className="history-list">
    {rows.map((row) => <li key={row.run_id}>
      <a href={`#run/${row.run_id}`} className="history-row">
        <span className="asset-mark" aria-hidden="true">{row.symbol.slice(0, 3)}</span>
        <span className="history-asset"><strong>{row.symbol}</strong><small>{date(row.created_at)}</small>{showModel && <small>{row.status === 'demo' || row.status === 'unavailable' ? '未调用模型' : row.model} · v{row.version}</small>}</span>
        <ReportBadge status={row.status} /><ArrowUpRight size={16} className="history-arrow" aria-hidden="true" />
      </a>
    </li>)}
  </ul>
}

function StartResearch({ mode, settings, onStarted, initialAsset }: { mode: Mode; settings?: Settings; onStarted: (run: Run) => void; initialAsset: string }) {
  const [asset, setAsset] = useState(initialAsset || 'BTC')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const isDemo = mode === 'demo' || (mode === 'server' && settings?.demo_mode)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    const symbol = asset.trim()
    if (!validAsset.test(symbol)) {
      setError('请输入有效的资产代码或 CoinGecko ID。')
      return
    }
    setError(''); setSubmitting(true)
    try {
      const run = await post<Run>('/research/runs', { symbol, ...(mode !== 'server' && { demo_mode: mode === 'demo' }) })
      onStarted(run)
    } catch (error) { setError(explain(error)) }
    finally { setSubmitting(false) }
  }
  return <section className="new-research" aria-labelledby="start-title">
    <div className="panel-heading"><h2 id="start-title">发起研究</h2>{isDemo && <span className="badge tone-demo"><FlaskConical size={13} />演示模式</span>}</div>
    <form onSubmit={submit}>
      <label className="visually-hidden" htmlFor="asset">研究资产</label>
      <div className="start-input">
        <div className="input-wrap"><Search size={16} /><input id="asset" value={asset} onChange={(event) => setAsset(event.target.value)} required maxLength={64} placeholder="例如 BTC 或 bitcoin" autoComplete="off" spellCheck={false} /></div>
        <button className="button primary" type="submit" disabled={submitting}>{submitting ? '正在提交' : '开始研究'}<ArrowRight size={17} /></button>
      </div>
      <div className="suggestions"><span>常用资产</span>{assets.map(({ symbol, name }) => <button key={symbol} type="button" aria-label={`${symbol} ${name}`} aria-pressed={asset.trim().toUpperCase() === symbol} onClick={() => setAsset(symbol)}>{symbol}</button>)}</div>
    </form>
    {error && <p className="notice danger" role="alert"><CircleAlert size={16} />{error}</p>}
    {!error && !isDemo && settings && !settings.model.configured && <p className="setup-hint"><CircleAlert size={15} />模型尚未配置。<a href="#settings">打开设置</a>可启用演示模式。</p>}
  </section>
}

function SettingsView({ settings, mode, onMode, error, refresh }: { settings?: Settings; mode: Mode; onMode: (mode: Mode) => void; error: string; refresh: () => void }) {
  return <>
    <SectionTitle title="设置" description="选择本浏览器发起研究时使用的模式，并查看服务端配置。" />
    <div className="workbench-grid settings-grid">
      <section className="panel">
        <div className="panel-heading"><h2><FlaskConical />研究模式</h2></div>
        <fieldset className="mode-select">
          <legend className="visually-hidden">研究模式</legend>
          {([
            ['server', '跟随服务端', settings ? `当前服务端默认：${settings.demo_mode ? '演示' : '真实研究'}` : '使用服务端默认配置'],
            ['live', '真实研究', '使用服务端配置的模型和外部数据源。'],
            ['demo', '演示模式', '使用示例行情，不请求外部数据源或模型。'],
          ] as const).map(([value, label, detail]) => <label key={value}>
            <input type="radio" name="research-mode" checked={mode === value} onChange={() => onMode(value)} />
            <span><strong>{label}</strong><small>{detail}</small></span>
          </label>)}
        </fieldset>
        <p className="subtle">此设置仅影响新发起的完整研究。</p>
      </section>
      <section className="panel">
        <div className="panel-heading"><h2><Database />服务配置</h2><button className="icon-button" type="button" onClick={refresh} aria-label="刷新服务配置"><RefreshCw size={17} /></button></div>
        {error ? <p className="notice danger" role="alert">{error}</p> : settings ? <dl className="config-list">
          <div><dt>模型供应商</dt><dd>{settings.model.provider}</dd></div>
          <div><dt>模型名称</dt><dd>{settings.model.name}</dd></div>
          <div><dt>模型密钥</dt><dd>{settings.model.configured ? '已配置' : '未配置'}</dd></div>
          <div><dt>CoinGecko</dt><dd>{settings.coingecko.plan === 'demo' ? '公开 / Demo API' : settings.coingecko.plan}</dd></div>
          <div><dt>Tavily 密钥</dt><dd>{settings.tavily.configured ? '已配置' : '未配置'}</dd></div>
        </dl> : <p className="subtle" role="status">正在读取配置…</p>}
        <p className="source-note">密钥仅保存在服务端环境中。</p>
      </section>
    </div>
  </>
}

function App() {
  const [view, setView] = useState(route)
  const [mode, setMode] = useState<Mode>(readMode)
  const [health, setHealth] = useState<Health>()
  const [connection, setConnection] = useState<'checking' | 'online' | 'offline'>('checking')
  const [settings, setSettings] = useState<Settings>()
  const [configError, setConfigError] = useState('')
  const [configRefresh, setConfigRefresh] = useState(0)
  const [historyRefresh, setHistoryRefresh] = useState(0)
  const [rows, setRows] = useState<ReportRow[]>([])
  const [historyError, setHistoryError] = useState('')
  const [historyLoading, setHistoryLoading] = useState(true)
  const [offset, setOffset] = useState(0)
  const [filterAsset, setFilterAsset] = useState('')
  const [filter, setFilter] = useState<{ symbol: string; status: ReportStatus | '' }>({ symbol: '', status: '' })
  const pageSize = 8
  const refreshHistory = useCallback(() => setHistoryRefresh((value) => value + 1), [])
  const research = useResearch(view.id, refreshHistory)
  const { report, run } = research
  const researchName = report?.symbol ?? run?.symbol
  const newResearch = researchName && validAsset.test(researchName) ? `#workbench/${researchName}` : '#workbench'

  useEffect(() => {
    function changed() { setView(route()); window.scrollTo({ top: 0 }) }
    window.addEventListener('hashchange', changed)
    return () => window.removeEventListener('hashchange', changed)
  }, [])

  useEffect(() => {
    const abort = new AbortController()
    const refresh = () => {
      const signal = abort.signal
      void api<Health>('/health', { signal }).then((next) => { setHealth(next); setConnection('online') }).catch(() => {
        if (!signal.aborted) setConnection('offline')
      })
      void api<Settings>('/settings', { signal }).then((next) => { setSettings(next); setConfigError('') }).catch((error) => {
        if (!signal.aborted) { setSettings(undefined); setConfigError(explain(error)) }
      })
    }
    refresh()
    const timer = window.setInterval(refresh, 30000)
    return () => { abort.abort(); window.clearInterval(timer) }
  }, [configRefresh])

  useEffect(() => {
    const abort = new AbortController()
    const start = view.page === 'history' ? offset : 0
    const query = new URLSearchParams({ limit: String(pageSize + 1), offset: String(start) })
    if (view.page === 'history') {
      if (filter.symbol) query.set('symbol', filter.symbol)
      if (filter.status) query.set('status', filter.status)
    }
    setHistoryLoading(true); setHistoryError(''); setRows([])
    void api<ReportRow[]>(`/research?${query}`, { signal: abort.signal }).then((records) => {
      if (!abort.signal.aborted) setRows(records)
    }).catch((error) => {
      if (!abort.signal.aborted) setHistoryError(explain(error))
    }).finally(() => { if (!abort.signal.aborted) setHistoryLoading(false) })
    return () => abort.abort()
  }, [view.page, offset, filter, historyRefresh])

  const failedRun = run?.state === 'failed'
  const runFailure = run?.error === 'interrupted' ? '服务重启时研究尚未完成，可以发起一项新研究。'
    : run?.error === 'timeout' ? '研究超时，没有生成报告。' : '运行未能完成，没有生成报告。'
  const historyProps = { loading: historyLoading, error: historyError, onRetry: refreshHistory }
  const networkText = { checking: '正在连接', online: '服务在线', offline: '服务离线' }[connection]
  return <>
    <a className="skip-link" href="#main-content" onClick={(event) => { event.preventDefault(); document.getElementById('main-content')?.focus() }}>跳到主要内容</a>
    <div className="app-shell">
      <BrandRail health={health} />
      <div className="app-body">
        <header className="topbar">
          <div className="topbar-inner">
            <Navigation page={view.page} />
            <span className="service-pill" role="status"><StatusDot tone={connection === 'online' ? 'green' : connection === 'offline' ? 'red' : 'muted'} />{networkText}</span>
          </div>
        </header>
        <main className="main" id="main-content" tabIndex={-1}>
          {view.page === 'settings' ? <SettingsView settings={settings} mode={mode} error={configError} refresh={() => setConfigRefresh((value) => value + 1)} onMode={(next) => {
            setMode(next)
            try { window.localStorage.setItem('spoonos-research-mode', next) } catch { /* Storage is optional. */ }
          }} /> : view.page === 'question' ? <>
            <SectionTitle title="快速问答" description="适合快速查询行情和指标。需要保存来源和结论时，请发起完整研究。" />
            <section className="panel question-panel"><div className="panel-heading"><h2><CircleHelp />向 SpoonOS 提问</h2></div><QuestionBox /></section>
          </> : view.page === 'history' ? <>
            <SectionTitle title="研究记录" description="重新打开已保存的报告，核对当时的数据、结论和引用。" action={<a href="#workbench" className="button primary"><Plus size={17} />新建研究</a>} />
            <section className="panel history-panel">
              <div className="panel-heading"><h2><History />已保存的报告</h2><button className="icon-button" type="button" onClick={refreshHistory} aria-label="刷新研究记录"><RefreshCw size={17} /></button></div>
              <form className="history-filter" onSubmit={(event) => {
                event.preventDefault()
                setOffset(0)
                setFilter((previous) => ({ ...previous, symbol: filterAsset.trim() }))
              }}>
                <label>资产代码<input type="search" value={filterAsset} pattern="[A-Za-z0-9\-]+" maxLength={64} placeholder="全部资产" onChange={(event) => setFilterAsset(event.target.value)} /></label>
                <label>报告状态<select value={filter.status} onChange={(event) => {
                  setOffset(0)
                  setFilter((previous) => ({ ...previous, status: event.target.value as ReportStatus | '' }))
                }}><option value="">全部状态</option>{Object.entries(reportLabels).map(([key, label]) => <option value={key} key={key}>{label}</option>)}</select></label>
                <button className="button secondary" type="submit"><Search size={15} />筛选</button>
              </form>
              <HistoryRows {...historyProps} rows={rows.slice(0, pageSize)} filtered={!!(filter.symbol || filter.status)} showModel />
              {(offset > 0 || rows.length > pageSize) && <div className="pagination"><button className="button secondary" type="button" disabled={historyLoading || offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}><ArrowLeft size={15} />上一页</button><span>第 {offset / pageSize + 1} 页</span><button className="button secondary" type="button" disabled={historyLoading || rows.length <= pageSize} onClick={() => setOffset(offset + pageSize)}>下一页<ArrowRight size={15} /></button></div>}
            </section>
          </> : view.id ? <>
            <div className="breadcrumb"><a href="#workbench">研究工作台</a><ChevronRight size={14} aria-hidden="true" /><span>{report ? '研究报告' : '研究运行'}</span></div>
            <SectionTitle title={researchName ? `${researchName} 研究` : '研究详情'}
              description={report ? `快照时间：${date(report.created_at)}` : '查看本次研究的执行进度。'}
              action={<a className="button secondary" href={newResearch}><Plus size={17} />{researchName ? '重新分析' : '新建研究'}</a>} />
            <a className="text-link mobile-execution" href="#execution-log" onClick={(event) => { event.preventDefault(); document.getElementById('execution-log')?.focus() }}><Activity size={15} />跳到执行日志</a>
            <div className="workbench-grid">
              <div className="workbench-main">
                {research.error ? <section className="panel" role="alert"><p className="notice danger">{research.error}</p><button className="button secondary" type="button" onClick={research.retry}>重试</button></section>
                  : report ? <><div className="snapshot-meta"><ReportBadge status={report.status} /><span className="snapshot-id" title={report.snapshot_id}>快照 <code>{report.snapshot_id}</code> · v{report.version}</span></div><ReportContent key={report.run_id} report={report} /></>
                  : failedRun ? <section className="panel"><p className="notice danger" role="alert"><CircleAlert size={16} />{runFailure}</p><a className="text-link" href={newResearch}>重新发起 <ArrowRight size={15} /></a></section>
                  : <section className="panel waiting"><span className="waiting-mark"><Activity size={24} /></span><h2>{run?.state === 'finished' ? '正在读取已保存的报告' : run?.state === 'queued' ? '研究已提交，等待执行' : run?.state === 'running' ? '正在收集和分析数据' : '正在读取研究状态'}</h2><p>完成后，报告会自动保存并显示在这里。</p></section>}
              </div>
              <aside className="right-rail" aria-label="本次研究的执行日志"><Execution run={run} report={report} events={research.steps} connection={research.connection} selected /></aside>
            </div>
          </> : <>
            <section className="research-cover" aria-labelledby="workbench-title">
              <div className="cover-content">
                <h1 id="workbench-title">加密资产 <span>研究工作台</span></h1>
                <p>输入资产代码或 CoinGecko ID，查看行情、指标和新闻证据。</p>
                <StartResearch mode={mode} settings={settings} initialAsset={view.asset} key={view.asset} onStarted={(job) => { window.location.hash = `run/${job.run_id}` }} />
              </div>
              <figure className="cover-plate">
                <img src={coverImage} alt="黑白照片，向上仰望排列整齐的建筑窗格" fetchPriority="high" />
                <figcaption>建筑网格</figcaption>
              </figure>
            </section>
            <div className="research-index">
              <section className="panel recent" aria-labelledby="recent-title">
                <div className="panel-heading"><h2 id="recent-title"><History />最近研究</h2><a href="#history" className="text-link">查看全部 <ArrowRight size={15} /></a></div>
                <HistoryRows {...historyProps} rows={rows.slice(0, 4)} />
              </section>
              <Execution events={{}} connection="closed" selected={false} />
              <Sources settings={settings} mode={mode} />
            </div>
          </>}
        </main>
      </div>
    </div>
  </>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
