import { AgentAvatar } from '../agents'
import { AGENTS, type AgentId } from '../agentList'
import type { AgentState } from '../derive'

type Props = { states: Record<AgentId, AgentState>; running: boolean }

export function AgentFloor({ states, running }: Props) {
  const boss = AGENTS[0]
  const team = AGENTS.slice(1)
  return (
    <div className="floor">
      <AgentCard meta={boss} state={states.boss} running={running} lead />
      <div className="floor-wire" aria-hidden="true" />
      <div className="floor-team">
        {team.map((m) => (
          <AgentCard key={m.id} meta={m} state={states[m.id]} running={running} />
        ))}
      </div>
    </div>
  )
}

function AgentCard({ meta, state, running, lead }: {
  meta: (typeof AGENTS)[number]; state: AgentState; running: boolean; lead?: boolean
}) {
  const label = state.status === 'working' ? 'Working' : state.status === 'done' ? 'Done' : running ? 'Standing by' : 'Idle'
  return (
    <article
      className={`agent agent-${state.status} ${lead ? 'agent-lead' : ''}`}
      style={{ '--agent': meta.color, '--agent-tint': meta.tint } as React.CSSProperties}
    >
      {state.status === 'working' && (
        <div className="bubble" role="status">
          {state.line ?? 'Thinking…'}
          <span className="typing" aria-hidden="true"><i /><i /><i /></span>
        </div>
      )}
      <div className="agent-figure">
        <AgentAvatar id={meta.id} size={lead ? 104 : 84} />
        {state.status === 'done' && <span className="agent-check" aria-label="done">✓</span>}
      </div>
      <h3>{meta.name}</h3>
      <p className="agent-role">{meta.role}</p>
      <span className="agent-status">{label}</span>
    </article>
  )
}
