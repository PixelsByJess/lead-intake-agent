# Case Study — Lead Intake Agent

**One-line:** An LLM agent that takes a raw inbound lead and acts on it — qualify, record, alert, draft, or escalate — with Claude owning the control flow.

## The problem

Inbound leads arrive messy and across channels. The busy work of qualifying them, logging them, and following up fast is exactly what gets dropped. Most "automations" for this are rigid pipelines: a human wires every branch in advance, and the LLM just fills one box.

## Approach

Invert the control flow.

Instead of pre-deciding every step, give Claude:

1. A clear goal (qualify and act)
2. Four tool schemas
3. Safety rules (always log; never email spam; escalate when unsure)
4. A turn-limit cap

That is the difference between a **pipeline** and an **agent** — and it is the part worth showing.

Tools stay **local-first** on purpose. Each one mirrors a real integration (Airtable, Gmail, Slack) and can be swapped without touching the agent loop.

## What was built

| Piece | Status |
|---|---|
| Python agent loop (`agent.py`) | Functional |
| Tool schemas + local handlers (`tools.py`) | Functional |
| Three sample leads (hot / warm / spam) | Functional |
| n8n workflow starter + proof GIFs | Demonstrated (related mirror) |
| Live Airtable / Gmail / Slack | Not yet — stubs write to `data/` |

## Result

| Evidence | Label |
|---|---|
| Distinct tool sequences across sample leads | `real` (reproducible with API key) |
| Spam path creates record + human flag, no email draft | `real` (by design + sample run) |
| n8n hot/spam run GIFs | `real` |
| Time saved / leads recovered | `placeholder` until real volume |

## What I'd do differently

Ship one real integration (Airtable) earlier so the story is "running against a live CRM," not only local JSON. Capture console screenshots of every `[tool call]` / `[tool result]` as portfolio proof assets on day one.

## Interview answer (45 seconds)

> Most lead automations are rigid pipelines. I inverted that. I gave the model a goal — qualify and act — and four tools: create CRM record, notify owner, draft follow-up, flag for human. On a hot lead it records, alerts, and drafts. On spam it records and escalates with no email. The interesting part isn't the tools; it's that the model owns the sequence. Next step is swapping the local CRM stub for a live Airtable write.
