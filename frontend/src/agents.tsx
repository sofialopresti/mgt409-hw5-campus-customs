// The five agents as little cartoon characters, each dressed for their job.
import type { ReactNode } from 'react'
import type { AgentId } from './agentList'

const INK = '#2E2C29'
const SKIN = '#EDCDB0'
const CHEEK = '#E2A48F'

type Props = { id: AgentId; size?: number }

/** Shared body: shadow, torso, neck, head, cheeks. Accessories layer behind (back) and over (front). */
function Figure({ color, back, front, face, size = 96 }: {
  color: string; back?: ReactNode; front?: ReactNode; face?: ReactNode; size?: number
}) {
  return (
    <svg viewBox="0 0 120 130" width={size} height={size * (130 / 120)} aria-hidden="true">
      <ellipse cx="60" cy="125" rx="36" ry="4" fill={INK} opacity="0.08" />
      {back}
      <path d="M28 124 Q28 76 60 74 Q92 76 92 124 Z" fill={color} />
      <rect x="54" y="66" width="12" height="10" rx="4" fill={SKIN} />
      <circle cx="60" cy="47" r="24" fill={SKIN} />
      <circle cx="46" cy="55" r="3.6" fill={CHEEK} opacity="0.55" />
      <circle cx="74" cy="55" r="3.6" fill={CHEEK} opacity="0.55" />
      {face ?? (
        <>
          <circle cx="51" cy="47" r="2.6" fill={INK} />
          <circle cx="69" cy="47" r="2.6" fill={INK} />
          <path d="M52 57 Q60 63 68 57" stroke={INK} strokeWidth="2.2" fill="none" strokeLinecap="round" />
        </>
      )}
      {front}
    </svg>
  )
}

// The Boss is drawn after Sofia: long dark-brown hair with a center part, brown eyes,
// a soft smile, a white eyelet blouse, a gold hoop earring and a gold circle necklace.
const HAIR = '#3B2A24'
const GOLD = '#C4A15A'
const BLOUSE_LINE = '#D8CFC2'

function Boss({ size }: { size?: number }) {
  const eyelets = [86, 94, 102, 110, 118]
  return (
    <Figure
      size={size}
      color="#F7F3EC"
      back={
        <path
          d="M33 48 Q31 19 60 19 Q89 19 87 48 L90 104 Q87 112 77 110 L43 110 Q33 112 30 104 Z"
          fill={HAIR}
        />
      }
      face={
        <>
          <path d="M45 41.5 Q50.5 38.5 55.5 41" stroke={HAIR} strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <path d="M75 41.5 Q69.5 38.5 64.5 41" stroke={HAIR} strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <circle cx="51" cy="47.5" r="2.9" fill="#4A2E22" />
          <circle cx="69" cy="47.5" r="2.9" fill="#4A2E22" />
          <circle cx="52" cy="46.5" r="0.9" fill="#fff" />
          <circle cx="70" cy="46.5" r="0.9" fill="#fff" />
          <path d="M47.5 45.5 L45.5 44 M48 47 L45.8 46.6" stroke={INK} strokeWidth="1" strokeLinecap="round" />
          <path d="M72.5 45.5 L74.5 44 M72 47 L74.2 46.6" stroke={INK} strokeWidth="1" strokeLinecap="round" />
          <path d="M58.5 51 Q60 53.5 61.5 51" stroke="#C99A80" strokeWidth="1.2" fill="none" strokeLinecap="round" />
          <path d="M52.5 57 Q60 62.5 67.5 57 Q60 59.5 52.5 57 Z" fill="#C98A86" />
          <path d="M52.5 57 Q60 62.5 67.5 57" stroke="#A86E6A" strokeWidth="1.2" fill="none" strokeLinecap="round" />
        </>
      }
      front={
        <>
          {/* top of the hair with a center part, and the long sides falling over the shoulders */}
          <path d="M35.5 46 Q35 21 59.4 21.5 Q47 27 43 40 Q40 44 35.5 46 Z" fill={HAIR} />
          <path d="M84.5 46 Q85 21 60.6 21.5 Q73 27 77 40 Q80 44 84.5 46 Z" fill={HAIR} />
          <path d="M35.5 44 Q36.5 60 40 70 Q42 84 40 100 Q35 102 31 96 Q33 76 33 58 Z" fill={HAIR} />
          <path d="M84.5 44 Q83.5 60 80 70 Q78 84 80 100 Q85 102 89 96 Q87 76 87 58 Z" fill={HAIR} />
          {/* gold hoop earring */}
          <rect x="35.6" y="55" width="3.4" height="6" rx="1.7" stroke={GOLD} strokeWidth="1.2" fill="none" />
          {/* blouse: outline, open collar, eyelet embroidery */}
          <path d="M28 124 Q28 76 60 74 Q92 76 92 124" stroke={BLOUSE_LINE} strokeWidth="1.4" fill="none" />
          <path d="M52 75 L60 92 L68 75 Z" fill={SKIN} />
          <path d="M50 74.5 L60 93 L70 74.5" stroke={BLOUSE_LINE} strokeWidth="1.6" fill="none" strokeLinejoin="round" />
          {eyelets.map((y) => (
            <g key={y} fill="none" stroke={BLOUSE_LINE} strokeWidth="1">
              <ellipse cx="46" cy={y} rx="1.6" ry="2.4" />
              <ellipse cx="74" cy={y} rx="1.6" ry="2.4" />
            </g>
          ))}
          {/* gold necklace with a circle pendant */}
          <path d="M53.5 76 Q60 90 66.5 76" stroke={GOLD} strokeWidth="0.9" fill="none" />
          <circle cx="60" cy="86.5" r="2.3" stroke={GOLD} strokeWidth="1.3" fill="none" />
          {/* still the Boss: briefcase */}
          <g transform="translate(84 96)">
            <rect x="0" y="4" width="26" height="19" rx="3" fill="#6B5444" />
            <path d="M8 4 V1 Q8 -1 10 -1 H16 Q18 -1 18 1 V4" stroke="#6B5444" strokeWidth="2.4" fill="none" />
            <rect x="0" y="11" width="26" height="2" fill="#5A4639" />
          </g>
        </>
      }
    />
  )
}

function Inventory({ size }: { size?: number }) {
  return (
    <Figure
      size={size}
      color="#A67C52"
      front={
        <>
          <path d="M35 41 Q35 19 60 19 Q85 19 85 41 Z" fill="#7F6347" />
          <rect x="34" y="36" width="52" height="8" rx="4" fill="#6E553C" />
          <circle cx="60" cy="16" r="5.5" fill="#6E553C" />
          <path d="M44 76 L44 124 M76 76 L76 124" stroke="#8C6741" strokeWidth="5" />
          <g transform="translate(36 86)">
            <rect x="0" y="0" width="48" height="32" rx="2" fill="#D2AE84" stroke="#A67C52" strokeWidth="1.5" />
            <rect x="20" y="0" width="8" height="32" fill="#E8D6BC" />
            <text x="6" y="22" fontSize="8" fontFamily="ui-monospace, monospace" fill="#7A5A3A">SKU</text>
          </g>
          <circle cx="36" cy="98" r="5" fill={SKIN} />
          <circle cx="84" cy="98" r="5" fill={SKIN} />
        </>
      }
    />
  )
}

function Accounting({ size }: { size?: number }) {
  return (
    <Figure
      size={size}
      color="#6F8F72"
      face={
        <>
          <circle cx="51" cy="47" r="2.3" fill={INK} />
          <circle cx="69" cy="47" r="2.3" fill={INK} />
          <circle cx="51" cy="47" r="6.5" stroke={INK} strokeWidth="1.8" fill="none" />
          <circle cx="69" cy="47" r="6.5" stroke={INK} strokeWidth="1.8" fill="none" />
          <path d="M57.5 47 H62.5" stroke={INK} strokeWidth="1.8" />
          <path d="M54 58 Q60 61 66 58" stroke={INK} strokeWidth="2" fill="none" strokeLinecap="round" />
        </>
      }
      front={
        <>
          <path d="M38 36 Q42 24 60 24 Q78 24 82 36 Q72 30 60 30 Q48 30 38 36 Z" fill="#8B6B57" />
          <path d="M33 37 Q60 28 87 37 L85 43 Q60 35 35 43 Z" fill="#7FA184" opacity="0.92" />
          <rect x="33" y="36" width="54" height="3.5" rx="1.75" fill="#5E7D62" />
          <rect x="80" y="28" width="3" height="18" rx="1" transform="rotate(25 81 37)" fill="#D9B45F" />
          <path d="M60 76 V124" stroke="#5E7D62" strokeWidth="1.5" />
          <circle cx="56" cy="92" r="1.6" fill="#E5ECE3" />
          <circle cx="56" cy="104" r="1.6" fill="#E5ECE3" />
          <g transform="translate(78 90)">
            <rect x="0" y="0" width="24" height="30" rx="3" fill="#3F4A44" />
            <rect x="3" y="3" width="18" height="7" rx="1" fill="#CFD8C9" />
            {[0, 1, 2].map((r) =>
              [0, 1, 2].map((c) => <rect key={`${r}${c}`} x={4 + c * 6} y={13 + r * 5.5} width="4" height="3.5" rx="0.8" fill="#9AA79E" />),
            )}
          </g>
          <circle cx="80" cy="104" r="5" fill={SKIN} />
        </>
      }
    />
  )
}

function Facilities({ size }: { size?: number }) {
  return (
    <Figure
      size={size}
      color="#8A8F86"
      front={
        <>
          <path d="M34 39 Q34 16 60 16 Q86 16 86 39 Z" fill="#C9A55A" />
          <path d="M60 16 V38" stroke="#B08A45" strokeWidth="3" />
          <rect x="29" y="36" width="62" height="7" rx="3.5" fill="#B08A45" />
          <path d="M40 124 V90 Q40 84 46 84 H74 Q80 84 80 90 V124 Z" fill="#B08A45" />
          <path d="M44 84 L40 76 M76 84 L80 76" stroke="#B08A45" strokeWidth="5" strokeLinecap="round" />
          <rect x="53" y="92" width="14" height="10" rx="2" fill="#9C7A3C" />
          <rect x="30" y="108" width="60" height="6" rx="2" fill="#6B5444" />
          <g transform="translate(88 82) rotate(20)">
            <rect x="-2" y="6" width="5" height="30" rx="2" fill="#8A8F94" />
            <path d="M-6 0 Q0 -4 6 0 L6 6 Q3 4 3 8 H-2 Q-2 4 -6 6 Z" fill="#8A8F94" />
          </g>
          <circle cx="86" cy="104" r="5" fill={SKIN} />
        </>
      }
    />
  )
}

function CustomerService({ size }: { size?: number }) {
  return (
    <Figure
      size={size}
      color="#A26D7E"
      face={
        <>
          <path d="M48 47 Q51 44 54 47" stroke={INK} strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <path d="M66 47 Q69 44 72 47" stroke={INK} strokeWidth="2.2" fill="none" strokeLinecap="round" />
          <path d="M51 56 Q60 66 69 56 Z" fill="#7A3E4A" />
        </>
      }
      back={<circle cx="60" cy="19" r="10" fill="#5A4036" />}
      front={
        <>
          <path d="M36 42 Q37 22 60 22 Q83 22 84 42 Q76 30 60 31 Q44 30 36 42 Z" fill="#5A4036" />
          <path d="M34 47 Q34 18 60 18 Q86 18 86 47" stroke="#3F3A36" strokeWidth="3" fill="none" />
          <rect x="29" y="41" width="9" height="14" rx="3.5" fill="#3F3A36" />
          <rect x="82" y="41" width="9" height="14" rx="3.5" fill="#3F3A36" />
          <path d="M34 54 Q36 65 48 63" stroke="#3F3A36" strokeWidth="2.4" fill="none" />
          <circle cx="49" cy="63" r="3" fill="#3F3A36" />
          <rect x="65" y="84" width="18" height="10" rx="2" fill="#F4F1EC" />
          <path d="M68 89 H80" stroke="#A26D7E" strokeWidth="1.5" />
        </>
      }
    />
  )
}

export function AgentAvatar({ id, size = 96 }: Props) {
  switch (id) {
    case 'boss':
      return <Boss size={size} />
    case 'inventory':
      return <Inventory size={size} />
    case 'accounting':
      return <Accounting size={size} />
    case 'facilities':
      return <Facilities size={size} />
    case 'customer_service':
      return <CustomerService size={size} />
  }
}
