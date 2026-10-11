import { useState } from 'react'
import type { BoardItem } from '../api'
import { money } from '../derive'

type Props = {
  items: BoardItem[]
  approver: string
  onApproverChange: (name: string) => void
  onApprove: (item: BoardItem) => Promise<string | null>
  disabled: boolean
}

export function Approvals({ items, approver, onApproverChange, onApprove, disabled }: Props) {
  const [busyId, setBusyId] = useState<number | null>(null)
  const [notes, setNotes] = useState<Record<number, string>>({})

  async function approve(item: BoardItem) {
    setBusyId(item.id)
    const error = await onApprove(item)
    setBusyId(null)
    if (error) setNotes((n) => ({ ...n, [item.id]: error }))
  }

  return (
    <section className="panel approvals" aria-label="Waiting for your approval">
      <header className="panel-head">
        <h2>Needs your OK</h2>
        <span className="count">{items.length}</span>
      </header>
      <label className="approver">
        <span>Approving as</span>
        <input value={approver} onChange={(e) => onApproverChange(e.target.value)} placeholder="Your name" />
      </label>
      {items.length === 0 ? (
        <p className="empty">Nothing waiting. Agents only <em>prepare</em> payments and purchase orders; they land here for you to approve.</p>
      ) : (
        <ul className="approval-list">
          {items.map((item) => {
            const isPay = item.kind === 'payment_request'
            const blocked = item.status === 'blocked_unpaid_invoice'
            return (
              <li key={item.id} className={`approval ${isPay ? 'approval-pay' : 'approval-po'}`}>
                <div className="approval-top">
                  <span className="approval-kind">{isPay ? 'Payment' : 'Purchase order'}</span>
                  <span className="muted">#{item.id} · ticket {item.ticket_id}</span>
                </div>
                {isPay ? (
                  <>
                    <p className="approval-amount">{money(item.data.amount)}</p>
                    <p className="approval-to">to {item.data.payee}</p>
                    <p className="approval-note">{item.data.description}</p>
                    <p className="approval-note">Checking {money(item.data.cash_before)} → {money(item.data.cash_after)}</p>
                  </>
                ) : (
                  <>
                    <p className="approval-amount">{money(item.data.total_cost)}</p>
                    <p className="approval-to">{item.title.replace(/^PO to /, '')}</p>
                    {blocked && <p className="approval-warn">Vendor is holding shipment until its open invoice is paid.</p>}
                    <p className="approval-note">Approving doesn't move money; the vendor bills later.</p>
                  </>
                )}
                {notes[item.id] && <p className="approval-error">{notes[item.id]}</p>}
                <button
                  className="btn btn-approve"
                  disabled={disabled || !approver.trim() || busyId === item.id}
                  onClick={() => approve(item)}
                >
                  {busyId === item.id ? 'Approving…' : isPay ? `Approve & pay ${money(item.data.amount)}` : 'Approve PO'}
                </button>
              </li>
            )
          })}
        </ul>
      )}
      {disabled && items.length > 0 && <p className="muted small">Approvals unlock when the agents finish.</p>}
    </section>
  )
}
