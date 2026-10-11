import { useEffect, useRef, useState } from 'react'
import type { Cash } from '../api'
import { money, type LedgerEntry } from '../derive'

function useAnimatedNumber(target: number | null, ms = 900): number | null {
  const [value, setValue] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target === null) return
    const start = from.current ?? target
    if (start === target) { setValue(target); return }
    const t0 = performance.now()
    let frame = 0
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / ms)
      const eased = 1 - Math.pow(1 - k, 3)
      setValue(start + (target - start) * eased)
      if (k < 1) frame = requestAnimationFrame(tick)
      else from.current = target
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, ms])
  return value
}

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null
  const w = 260, h = 54, pad = 4
  const max = Math.max(...points), min = Math.min(0, ...points)
  const x = (i: number) => pad + (i * (w - pad * 2)) / (points.length - 1)
  const y = (v: number) => pad + ((max - v) * (h - pad * 2)) / (max - min || 1)
  // step line: balances hold flat, then drop when a payment is approved
  let d = `M${x(0)} ${y(points[0])}`
  for (let i = 1; i < points.length; i++) d += ` H${x(i)} V${y(points[i])}`
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      <path d={`${d} V${h} H${x(0)} Z`} className="spark-fill" />
      <path d={d} className="spark-line" />
      {points.map((p, i) => <circle key={i} cx={x(i)} cy={y(p)} r="2.6" className="spark-dot" />)}
    </svg>
  )
}

export function CashCard({ cash, entries }: { cash: Cash | null; entries: LedgerEntry[] }) {
  const shown = useAnimatedNumber(cash?.balance ?? null)
  const [drop, setDrop] = useState<number | null>(null)
  const last = useRef<number | null>(null)

  useEffect(() => {
    if (!cash) return
    if (last.current !== null && cash.balance < last.current) {
      setDrop(cash.balance - last.current)
      const t = setTimeout(() => setDrop(null), 4000)
      last.current = cash.balance
      return () => clearTimeout(t)
    }
    last.current = cash.balance
  }, [cash])

  const series = entries.length ? [entries[0].cashAfter + entries[0].amount, ...entries.map((e) => e.cashAfter)] : []

  return (
    <section className="panel cash" aria-label="Checking balance">
      <header className="panel-head">
        <h2>Checking</h2>
        <span className="muted">as of {cash?.as_of ?? '—'}</span>
      </header>
      <p className="cash-balance">
        {shown === null ? '—' : money(shown)}
        {drop !== null && <span className="cash-drop">{money(drop)}</span>}
      </p>
      <p className="muted small">Cash only goes out in this shop. It drops when you approve a payment.</p>
      <Sparkline points={series} />
      {entries.length > 0 && (
        <ul className="ledger">
          {entries.map((e) => (
            <li key={e.seq}>
              <span>{e.payee}</span>
              <span className="ledger-amt">−{money(e.amount)}</span>
              <span className="ledger-who">approved by {e.approvedBy}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
