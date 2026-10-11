import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError, type AgentEvent, type BoardItem, type Cash, type Ticket } from './api'
import { ActivityFeed } from './components/ActivityFeed'
import { AgentFloor } from './components/AgentFloor'
import { Approvals } from './components/Approvals'
import { CashCard } from './components/CashCard'
import { Summary } from './components/Summary'
import { TicketList } from './components/TicketList'
import { activeRun, agentStates, latestDecision, latestRunEvents, ledger, sinceLastReset, STATUS_LABEL } from './derive'

// Events that change tickets, approvals, or cash: refresh those when one arrives.
const REFRESH_ON = new Set([
  'ticket_decision', 'payment_approval', 'payment_result', 'purchase_order_approval', 'purchase_order_refused',
  'database_reset', 'run_finished', 'agent_loop',
])

const message = (e: unknown) => (e instanceof ApiError || e instanceof Error ? e.message : String(e))

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [approvals, setApprovals] = useState<BoardItem[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [approver, setApprover] = useState(() => localStorage.getItem('approver') ?? '')
  const [error, setError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const lastSeq = useRef(0)

  const refreshDesk = useCallback(async () => {
    try {
      const [t, a, c] = await Promise.all([api.tickets(), api.approvals(), api.cash()])
      setTickets(t)
      setApprovals(a)
      setCash(c)
      setSelectedId((id) => id ?? t[0]?.id ?? null)
      setError(null)
    } catch (e) {
      setError(message(e))
    }
  }, [])

  const pollEvents = useCallback(async () => {
    try {
      const fresh = await api.events(lastSeq.current)
      if (!fresh.length) return
      lastSeq.current = fresh.at(-1)!.seq
      setEvents((prev) => [...prev, ...fresh])
      if (fresh.some((e) => REFRESH_ON.has(e.event))) refreshDesk()
    } catch (e) {
      setError(message(e))
    }
  }, [refreshDesk])

  useEffect(() => {
    refreshDesk()
    pollEvents()
  }, [refreshDesk, pollEvents])

  const current = useMemo(() => sinceLastReset(events), [events])
  const running = useMemo(() => activeRun(current), [current])

  // Poll fast while agents work, slowly otherwise (so runs started elsewhere still show up).
  useEffect(() => {
    const id = setInterval(pollEvents, running || starting ? 1200 : 4000)
    return () => clearInterval(id)
  }, [pollEvents, running, starting])

  const selected = tickets.find((t) => t.id === selectedId) ?? null
  const runEvents = useMemo(() => (selectedId ? latestRunEvents(current, selectedId) : []), [current, selectedId])
  const states = useMemo(() => agentStates(runEvents), [runEvents])
  const decision = useMemo(() => latestDecision(runEvents), [runEvents])
  const cashEntries = useMemo(() => ledger(current), [current])
  const selectedIsRunning = running?.ticketId === selectedId

  async function startTeam() {
    if (!selected) return
    setStarting(true)
    try {
      await api.runTicket(selected.id)
      await pollEvents()
    } catch (e) {
      setError(message(e))
    } finally {
      setStarting(false)
    }
  }

  async function approve(item: BoardItem): Promise<string | null> {
    try {
      await api.approve(item.id, approver.trim())
      await Promise.all([refreshDesk(), pollEvents()])
      return null
    } catch (e) {
      await refreshDesk()
      return message(e)
    }
  }

  async function reset() {
    if (!confirm('Reset the shop to its original data and clear the board? The audit trail keeps everything.')) return
    try {
      await api.reset()
      await Promise.all([refreshDesk(), pollEvents()])
    } catch (e) {
      setError(message(e))
    }
  }

  function changeApprover(name: string) {
    setApprover(name)
    localStorage.setItem('approver', name)
  }

  const canStart = !!selected && !running && !starting && selected.status !== 'resolved'
  const startLabel = starting ? 'Starting…' : selected?.state === 'resolved' ? 'Run the team again' : 'Start the agent team'

  return (
    <div className="page">
      <header className="masthead">
        <div>
          <p className="eyebrow">Campus Customs</p>
          <h1>Front Desk Board</h1>
        </div>
        <div className="masthead-right">
          <span className="date-chip">Shop date · {cash?.as_of ?? '—'}</span>
          <button className="btn btn-quiet" onClick={reset} disabled={!!running}>Fresh run (reset)</button>
        </div>
      </header>

      {error && (
        <div className="alert" role="alert">
          {error}
          <button className="alert-x" onClick={() => setError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <main className="layout">
        <TicketList tickets={tickets} selectedId={selectedId} runningId={running?.ticketId ?? null} onSelect={setSelectedId} />

        <div className="center">
          <section className="panel stage" aria-label="Agent team">
            <header className="panel-head">
              <div>
                <h2>{selected ? `Ticket #${selected.id} · ${selected.subject}` : 'Pick a ticket'}</h2>
                {selected && (
                  <p className="muted">
                    {selected.requester} · {selected.notes}
                  </p>
                )}
              </div>
              <button className="btn btn-primary" onClick={startTeam} disabled={!canStart}>
                {selectedIsRunning ? 'Team is working…' : startLabel}
              </button>
            </header>
            {running && !selectedIsRunning && (
              <p className="notice">The team is busy on ticket #{running.ticketId}. One ticket runs at a time.</p>
            )}
            {selected?.state === 'resolved' && !selectedIsRunning && (
              <p className="notice notice-done">
                Resolved by the team · outcome: <strong>{STATUS_LABEL[selected.status] ?? selected.status}</strong>
              </p>
            )}
            <AgentFloor states={states} running={selectedIsRunning} />
          </section>

          {decision && !selectedIsRunning && <Summary decision={decision} states={states} />}

          <section className="panel activity" aria-label="Activity">
            <header className="panel-head">
              <h2>Activity</h2>
              <span className="muted">{selectedIsRunning ? 'live' : 'latest run'}</span>
            </header>
            <ActivityFeed events={runEvents} />
          </section>
        </div>

        <aside className="side">
          <CashCard cash={cash} entries={cashEntries} />
          <Approvals
            items={approvals}
            approver={approver}
            onApproverChange={changeApprover}
            onApprove={approve}
            disabled={!!running}
          />
        </aside>
      </main>
    </div>
  )
}
