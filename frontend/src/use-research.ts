import { useEffect, useState } from 'react'
import { api, ApiError, explain, type Report, type Run, type Step } from './api'

interface Snapshot {
  id: string
  run?: Run
  report?: Report
  steps: Record<string, Step>
  connection: 'connecting' | 'live' | 'retrying' | 'closed'
  error?: string
}

const empty = (id: string): Snapshot => ({ id, steps: {}, connection: 'connecting' })

export function useResearch(id: string, onSaved: () => void) {
  const [snapshot, setSnapshot] = useState(() => empty(id))
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!id) return
    const abort = new AbortController()
    let stream: EventSource | undefined
    const signal = abort.signal
    setSnapshot(empty(id))
    const set = (update: (value: Snapshot) => Snapshot) => {
      if (!signal.aborted) setSnapshot((value) => value.id === id ? update(value) : value)
    }
    const showReport = async () => {
      try {
        const report = await api<Report>(`/research/${id}`, { signal })
        set((value) => ({ ...value, report, connection: 'closed' }))
      } catch (error) {
        set((value) => ({ ...value, connection: 'closed', error: explain(error) }))
      }
    }
    const open = async () => {
      let run: Run
      try {
        run = await api<Run>(`/research/runs/${id}`, { signal })
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) {
          await showReport() // Reports created by the legacy synchronous API still open here.
        } else {
          set((value) => ({ ...value, connection: 'closed', error: explain(error) }))
        }
        return
      }
      if (signal.aborted) return
      set((value) => ({ ...value, run }))
      if (run.state === 'finished') { await showReport(); return }
      // Replay a failed run too so its partial execution timeline stays inspectable.
      stream = new EventSource(`/research/runs/${id}/events`)
      stream.onopen = () => set((value) => ({ ...value, connection: 'live' }))
      stream.onerror = () => set((value) => ({ ...value, connection: 'retrying' }))
      stream.addEventListener('run', (event: MessageEvent<string>) => {
        const next: Run = JSON.parse(event.data)
        set((value) => !value.run || next.cursor >= value.run.cursor ? { ...value, run: next } : value)
      })
      stream.addEventListener('node', (event: MessageEvent<string>) => {
        const step: Step = JSON.parse(event.data)
        set((value) => ({ ...value, steps: { ...value.steps, [step.node]: step } }))
      })
      stream.addEventListener('terminal', (event: MessageEvent<string>) => {
        const final: Run = JSON.parse(event.data)
        stream?.close()
        set((value) => ({ ...value, run: final, connection: 'closed' }))
        if (final.state === 'finished') {
          void showReport()
          onSaved()
        }
      })
    }
    void open()
    return () => { abort.abort(); stream?.close() }
  }, [id, attempt, onSaved])

  return { ...(snapshot.id === id ? snapshot : empty(id)), retry: () => setAttempt((value) => value + 1) }
}
