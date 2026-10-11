# Front Desk Board — Design

The board (`frontend/`, React + Vite + TypeScript) is the human's view of the Campus Customs agent team. It calls the
desk API at `http://localhost:8000` and starts with `npm run dev` (http://localhost:5173).

## My specifications
- List all three tickets and let me pick one.
- Start the agent team on the ticket I picked.
- Show each agent as a **cartoon character of their role**, and show what they're doing while the ticket runs.
- Mark a ticket **resolved** once the team finishes it.
- Show a **short summary** of what the agents did.
- Leave space for a human to **approve a payment or purchase order**. Agents only prepare them.
- Show the **checking balance**, and have it visibly drop after I approve a payment.
- **Not neon.** Clean, but visually interesting, with no bright colors.
- **Not all beige either.** Add muted color so the page doesn't feel washed out.
- **The Boss should look like me** (Sofia).

## Overall look: a paper front desk
The look is a shop's front desk: paper tickets, a ledger, and rubber stamps. Bright colors would compete with the
information, so every color is muted, but there is enough of it (a slate header, color-coded tickets and agents,
a teal cash card) that the page doesn't read as beige.

| Element | Choice | Why |
|---|---|---|
| Background | Cool blue-grey `#E8EDF0` with a faint dot grid | Calm and tactile, like a desk blotter, and less beige so the colored cards stand out |
| Masthead | A deep slate-to-sage gradient band with light text | Gives the page a strong, colored anchor at the top without anything bright |
| Text | Soft ink `#2E2C29`. Headings in a serif (Iowan Old Style / Palatino); body in the system sans; numbers, SKUs and tool names in monospace | The serif makes it feel like a printed shop document. Monospace marks exact values the agents read from the database |
| Cards | Off-white panels, hairline borders, soft shadow, 14px corners | Clean structure without heavy boxes |
| Color | No bright colors, but plenty of muted color. Each agent has one role color; ticket types have their own (dusty blue, ochre, plum); state colors are sage = done, ochre = in progress / waiting, brick = errors or money leaving; and each panel has a colored top strip (tickets blue, activity plum, approvals sage) | Color always *means* something, so it never decorates for its own sake |
| Motion | Small and purposeful: working agents bob, speech bubbles pop in, new activity slides in, the cash number counts down. All of it turns off for "reduce motion" users | Motion only marks something that is happening now |

**Layout (3 columns):** tickets on the left, the agent team in the middle (with the summary and live activity
below it), and money on the right (checking balance on top, approvals underneath). On narrow screens the money
column moves under the others.

## How the agents read differently
Each agent is a small SVG cartoon dressed for their job and drawn in their own muted color. You can tell them
apart at a glance, even at 30px in the activity feed.

| Agent | Character | Color |
|---|---|---|
| The Boss | Drawn after Sofia: long dark-brown hair with a center part, brown eyes with lashes, soft smile, gold hoop earring, gold circle necklace, white eyelet blouse. The briefcase marks her as the Boss | Slate `#4B5A6E` card |
| Inventory | Beanie, overall straps, carrying a cardboard box marked "SKU" | Cardboard brown `#A67C52` |
| Accounting | Green visor, round glasses, pencil behind the ear, calculator | Sage `#6F8F72` |
| Facilities | Hard hat, work overalls, tool belt, wrench | Ochre `#B08A45` |
| Customer Service | Hair bun, headset with mic, big smile, name tag | Dusty rose `#A26D7E` |

- **Org chart:** the Boss sits on top, connected by a dashed line to the four specialists below, because the Boss
  delegates and they report back.
- **Card color:** every agent card has a top border in the agent's color and a light tint of it, so even idle cards
  read as that agent.
- **Three states per agent,** so you can see who's involved at a glance:
  - **Idle / Standing by:** slightly muted and faded. They aren't part of this ticket (yet).
  - **Working:** the card fills with the agent's tint and the character bobs. A speech bubble says what they're
    doing in plain words, such as "Counting stock on the shelf…" or "Previewing a payment…". It updates live from
    each MCP tool the agent calls.
  - **Done:** a check badge in the agent's color.
- **Activity feed:** every step is a timeline row with the agent's face, a plain-English line ("Inventory got a task
  from the Boss", "Accounting reported back"), and the exact MCP tool as a monospace chip, such as
  `check_stock(sku=CC-TEE-WHITE, size=S)`. The plain sentence is for the manager; the chip is for auditing.

## How resolved tickets show up
- **Tickets as paper stubs:** each ticket is drawn like a paper ticket, with punched notches, a dashed tear line
  above the SKU/lease detail, and an edge strip and type label in that ticket type's color: dusty blue for
  customer orders, ochre for rent notices, and plum for price overrides. The selected ticket fills with that tint.
- **Resolved:** when the team finishes a ticket, it gets a tilted sage **RESOLVED rubber stamp**, a sage edge strip,
  and a pill showing the Boss's actual outcome, such as "Resolved · Waiting on you". "Resolved" means the agents
  finished their work. The pill keeps the real outcome visible, so a ticket that still needs my approval doesn't
  look completely closed.
- **Open tickets** have a neutral edge, and the one being worked shows a pulsing ochre "Agents working" pill.
  Only one ticket can run at a time, so other tickets explain that the team is busy.
- **Summary:** after a run, "What the team did" shows the Boss's final call in a quote box, one line per agent
  that helped (in that agent's color), and a "Still on your plate" list of human follow-ups.

## How cash shows up
- **Checking card:** a dark teal "bank" card, the one dark panel on the page, so money is the first thing you see.
  It has faint ruled ledger lines and a large serif balance in tabular numbers.
- **Balance drops:** when I approve a payment, the balance **counts down** to the new amount, a brick-red delta tag
  (e.g. "−$2,400.00") appears briefly, and a **step chart** drops a level. It's a step chart rather than a smooth
  line because cash doesn't drift: it holds flat, then falls on a payment.
- **Ledger:** each payment is listed with the payee, amount, and who approved it, so every drop is explained.
- **Why it only goes down:** the card says cash only goes out in this shop, matching the project rule that no
  revenue is recorded.

## Approvals ("Needs your OK")
- **Approval cards:** agents only *prepare* payments and purchase orders, and each one waits here as its own card.
  - **Payments** have a sage top edge and show the amount, payee, and "Checking $X → $Y" before I approve.
  - **Purchase orders** have a cardboard top edge, and say that approving moves no money.
  - **Blocked POs** show an ochre note that the vendor is holding shipment until its invoice is paid.
- **Approving as:** I type my name once; it's remembered and saved as `approved_by`. Approve buttons stay disabled
  until a name is entered and while the agents are working.
- **Refusals stay visible:** if the server refuses (not enough cash, vendor still unpaid), the reason shows on the
  card instead of quietly failing.

## Other states
- **Fresh run (reset):** asks for confirmation, then resets the database and board. The audit trail keeps everything.
- **Backend not running:** a muted brick banner says so ("Is uvicorn running?") instead of showing a blank page.
