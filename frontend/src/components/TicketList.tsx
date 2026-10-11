import type { Ticket } from '../api'
import { STATUS_LABEL } from '../derive'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

function detailLine(t: Ticket): string {
  if (t.sku) return `${t.qty} × ${t.sku} · size ${t.size}`
  if (t.lease_id) return `Lease #${t.lease_id}`
  return t.type
}

type Props = {
  tickets: Ticket[]
  selectedId: number | null
  runningId: number | null
  onSelect: (id: number) => void
}

export function TicketList({ tickets, selectedId, runningId, onSelect }: Props) {
  return (
    <section className="panel tickets" aria-label="Tickets">
      <header className="panel-head">
        <h2>Desk tickets</h2>
        <span className="muted">{tickets.filter((t) => t.state === 'open').length} open</span>
      </header>
      <ul className="ticket-list">
        {tickets.map((t) => {
          const running = runningId === t.id
          return (
            <li key={t.id}>
              <button
                className={`ticket ticket-${t.type} ${selectedId === t.id ? 'is-selected' : ''} ${t.state === 'resolved' ? 'is-resolved' : ''}`}
                onClick={() => onSelect(t.id)}
              >
                <span className="ticket-top">
                  <span className="ticket-no">#{t.id}</span>
                  <span className="ticket-type">{TYPE_LABEL[t.type] ?? t.type}</span>
                </span>
                <span className="ticket-subject">{t.subject}</span>
                <span className="ticket-from">from {t.requester}</span>
                <span className="ticket-detail">{detailLine(t)}</span>
                <span className="ticket-foot">
                  {running ? (
                    <span className="pill pill-running"><span className="dot" /> Agents working</span>
                  ) : t.state === 'resolved' ? (
                    <span className="pill pill-resolved" title="Resolved by the agent team">{STATUS_LABEL[t.status] ?? t.status}</span>
                  ) : (
                    <span className="pill pill-open">Open</span>
                  )}
                  {t.state === 'resolved' && !running && <span className="stamp">Resolved</span>}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
