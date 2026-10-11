import type { AgentEvent } from '../api'
import { AgentAvatar } from '../agents'
import { agentMeta, type AgentId } from '../agentList'
import { formatArgs, shorten, STATUS_LABEL } from '../derive'

const SHOWN = new Set([
  'agent_started', 'tool_call', 'agent_loop', 'payment_approval', 'payment_refused_before_approval',
  'payment_duplicate_blocked', 'ticket_decision', 'agent_error', 'payment_result',
  'purchase_order_approval', 'purchase_order_refused',
])

function describe(e: AgentEvent): { title: string; body?: string | null } {
  const who = agentMeta(e.agent)?.name ?? (e.agent === 'human' ? 'You' : 'System')
  switch (e.event) {
    case 'agent_started':
      return e.agent === 'boss'
        ? { title: 'The Boss picked up the ticket' }
        : { title: `${who} got a task from the Boss`, body: shorten(e.summary, 220) }
    case 'tool_call':
      return { title: `${who} used a tool` }
    case 'agent_loop':
      return { title: `${who} reported back`, body: shorten(e.summary, 260) }
    case 'payment_approval':
      return { title: e.agent === 'human' ? 'You approved a payment' : 'A payment is waiting for your approval', body: e.summary }
    case 'payment_refused_before_approval':
      return { title: 'A payment was refused before reaching you', body: e.summary }
    case 'payment_duplicate_blocked':
      return { title: 'Accounting skipped a duplicate payment request' }
    case 'payment_result':
      return { title: 'Payment made', body: e.summary }
    case 'purchase_order_approval':
      return { title: 'You approved a purchase order', body: e.summary }
    case 'purchase_order_refused':
      return { title: 'Purchase order approval refused', body: e.summary }
    case 'ticket_decision':
      return { title: `Final call · ${STATUS_LABEL[e.detail?.status] ?? e.detail?.status ?? ''}` }
    case 'agent_error':
      return { title: `${who} hit an error`, body: e.summary }
    default:
      return { title: e.event }
  }
}

export function ActivityFeed({ events }: { events: AgentEvent[] }) {
  const shown = events.filter((e) => SHOWN.has(e.event))
  if (!shown.length) {
    return <p className="empty">Nothing yet. Start the agent team and their steps will appear here as they happen.</p>
  }
  return (
    <ol className="feed">
      {shown.map((e) => {
        const meta = agentMeta(e.agent)
        const { title, body } = describe(e)
        return (
          <li key={e.seq} className={`feed-item feed-${e.event}`} style={{ '--agent': meta?.color ?? '#6E6A64' } as React.CSSProperties}>
            <span className="feed-avatar">
              {meta ? <AgentAvatar id={meta.id as AgentId} size={30} /> : <span className="feed-human">{e.agent === 'human' ? '✎' : '•'}</span>}
            </span>
            <div className="feed-text">
              <p className="feed-title">
                {title}
                <time>{new Date(e.logged_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' })}</time>
              </p>
              {body && <p className="feed-body">{body}</p>}
              {e.tool_calls.length > 0 && (
                <div className="chips">
                  {e.tool_calls.map((c, i) => (
                    <code key={i} className="chip" title={formatArgs(c.args)}>
                      {c.tool}
                      {c.args && Object.keys(c.args).length > 0 && <span className="chip-args">({shorten(formatArgs(c.args), 60)})</span>}
                    </code>
                  ))}
                </div>
              )}
            </div>
          </li>
        )
      })}
    </ol>
  )
}
