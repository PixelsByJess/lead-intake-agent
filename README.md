# Lead Intake Agent

**Agent (tool-use) that qualifies an inbound lead and acts — create CRM record, notify owner, draft follow-up, or flag for human review.**

> Status: **functional local demo** (Python agent + sample leads).  
> Live CRM / Gmail / Slack integrations are intentionally stubbed as local JSON files so the control loop is easy to inspect and safe to run.  
> n8n proof GIFs of related hot/spam routing live under `proof/` (push from local if missing).

Built by [Jessica Rhein](https://github.com/PixelsByJess) · JessxAI

---

## Why this exists

Most "lead automations" are rigid pipelines: a human pre-wires every branch, and the model fills one box.

This project inverts that:

| Pipeline | Agent (this repo) |
|---|---|
| You hard-code `IF priority == Hot` | Model chooses tools and order |
| LLM only summarizes | LLM **acts** via tools |
| Spam still gets a template email unless you remembered a branch | Spam is recorded + escalated — **no email drafted** |

The interesting proof is not the tools. It's that **the model owns the sequence**.

---

## Architecture

```
Inbound lead (JSON)
        |
        v
+-----------------------+
|  Lead Intake Agent    |  Claude + tool-use loop
|  (goal + 4 tools)     |  max 8 turns (safety cap)
+-----------+-----------+
            |
   create / notify / draft / flag_for_human
            |
            v
     data/*.json  (local stand-ins for Airtable / Slack / Gmail)
```

### Tools

| Tool | Mirrors | Behavior |
|---|---|---|
| `create_crm_record` | Airtable / CRM | Always log the lead |
| `notify_owner` | Email / Slack | Alert on hot / urgent leads |
| `draft_followup_email` | Gmail draft | First reply for legitimate leads only |
| `flag_for_human` | Review queue | Spam, risk, or ambiguity |

---

## Quick start

```bash
cd lead-intake-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
export ANTHROPIC_API_KEY=sk-ant-...

python agent.py              # all 3 sample leads
python agent.py --lead hot
python agent.py --lead spam
```

### Expected behavior (qualitative)

| Lead id | Expected tools (typical) |
|---|---|
| `hot` | `create_crm_record` → `notify_owner` → `draft_followup_email` |
| `warm` | `create_crm_record` → optional notify/draft |
| `spam` | `create_crm_record` → `flag_for_human` · **no** draft email |

After a run, inspect `data/crm_records.json`, `data/notifications.json`, `data/draft_emails.json`, `data/human_flags.json`.

---

## n8n mirror

- Build guide: `docs/build-guide.md`
- Workflow starter: `n8n/n8n_workflow.json`
- Proof GIFs: `proof/` (hot + spam runs)

Python agent = control-flow story. n8n = ops/integration story.

---

## Case study (short)

**Problem:** Inbound leads are messy; qualification and follow-up get dropped.

**Approach:** Goal + four tool schemas. Model owns the sequence. Tools are local-first so Airtable/Gmail/Slack can swap in later.

**Result (demo):** Distinct routing across hot / warm / spam. Time-saved metrics are `placeholder` until real volume.

Full write-up: [`docs/case-study.md`](docs/case-study.md)

---

## Defensibility labels

| Claim | Label |
|---|---|
| Python agent loop with Anthropic tool-use | `real` |
| Distinct routing on 3 sample leads | `real` when re-run with API key |
| Production CRM / email integration | `not yet` — local stubs |
| Time-saved metrics | `placeholder` |

## License

MIT — see [LICENSE](LICENSE)
