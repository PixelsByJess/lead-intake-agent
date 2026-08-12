# Claude-Powered Lead Intake Automation — Build Guide

**Project goal:** Form → Claude extracts/scores → Airtable record → hot leads trigger alert.

**Skills this proves:** webhooks, JSON, Claude API, prompt engineering, Airtable, conditional logic, error handling, workflow documentation.

**Build in n8n first** (highest job relevance), then rebuild in Make for a second proof point.

For the **agent (tool-use) version**, see `agent.py` and `tools.py` in the repo root. That build is the control-flow story; this guide is the ops pipeline story.

---

## Phase 0 — Prep

### Airtable base: Lead Intake CRM → table `Leads`

| Field | Type |
|---|---|
| Name | Single line text |
| Email | Email |
| Company | Single line text |
| Inquiry | Long text |
| Service Interest | Single select |
| Lead Score | Number 0–100 |
| Priority | Hot / Warm / Cold |
| AI Summary | Long text |
| Suggested Reply | Long text |
| Status | New / Contacted / Qualified / Closed |
| Created | Created time |

Create an Airtable personal access token with `data.records:read` + `data.records:write`.

### Claude system prompt

```
You are a lead qualification assistant for a solo AI automation consultant.
Analyze the inquiry and respond with ONLY valid JSON, no markdown:
{
  "service_interest": "Automation" | "Web Design" | "Consulting" | "Other",
  "lead_score": <0-100 integer>,
  "priority": "Hot" | "Warm" | "Cold",
  "summary": "<2-sentence summary>",
  "suggested_reply": "<3-4 sentence friendly first reply>"
}
Scoring: Hot = 70+, Warm = 40-69, Cold = <40.
```

---

## n8n flow (summary)

1. **Form Trigger** — Name, Email, Company, Message
2. **HTTP Request** → `POST https://api.anthropic.com/v1/messages` (Header Auth `x-api-key`)
3. **Code node** — parse Claude JSON + merge form fields
4. **Airtable** — create record
5. **IF** priority equals Hot → email alert
6. **Error workflow** + retry on Claude node

Import the starter from `n8n/n8n_workflow.json` and add Airtable/Gmail credentials.

---

## Make flow (summary)

Webhook → Anthropic Claude module → Parse JSON → Airtable create → Router (Hot → email).

---

## Portfolio proof checklist

- [ ] n8n canvas screenshot
- [ ] Claude HTTP config (key redacted)
- [ ] Airtable with scored leads
- [ ] Hot-lead alert screenshot
- [ ] Error-handler test screenshot
- [ ] Agent console run (`python agent.py --lead hot` / `--lead spam`)

See also: [`case-study.md`](case-study.md)
