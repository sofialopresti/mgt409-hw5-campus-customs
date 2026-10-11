import type { TicketDecision } from '../api'
import { AgentAvatar } from '../agents'
import { AGENTS } from '../agentList'
import type { AgentState } from '../derive'
import { STATUS_LABEL } from '../derive'

type Props = { decision: TicketDecision; states: Record<string, AgentState> }

export function Summary({ decision, states }: Props) {
  const helpers = AGENTS.filter((a) => a.id !== 'boss' && states[a.id]?.summary)
  return (
    <section className="panel summary" aria-label="What the agents did">
      <header className="panel-head">
        <h2>What the team did</h2>
        <span className={`pill pill-status-${decision.status}`}>{STATUS_LABEL[decision.status] ?? decision.status}</span>
      </header>
      <div className="final-call">
        <AgentAvatar id="boss" size={44} />
        <div>
          <p className="eyebrow">The Boss's final call</p>
          <p>{decision.final_call}</p>
        </div>
      </div>
      {helpers.length > 0 && (
        <ul className="helper-list">
          {helpers.map((a) => (
            <li key={a.id} style={{ '--agent': a.color } as React.CSSProperties}>
              <strong>{a.name}</strong>
              <span>{states[a.id].summary}</span>
            </li>
          ))}
        </ul>
      )}
      {decision.human_follow_ups.length > 0 && (
        <div className="follow-ups">
          <p className="eyebrow">Still on your plate</p>
          <ul>
            {decision.human_follow_ups.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        </div>
      )}
    </section>
  )
}
