#!/usr/bin/env python3
"""
Lead Intake Agent

An LLM agent that qualifies an inbound lead and acts on it via tool use.
Claude owns the control flow: given a goal + tool schemas, it decides the
sequence (create CRM record, notify owner, draft follow-up, or flag for human).

This is an *agent*, not a hard-coded IF pipeline.

Usage:
  export ANTHROPIC_API_KEY=...
  python agent.py                     # run all sample leads
  python agent.py --lead hot          # run one sample by id
  python agent.py --file leads.json   # custom lead list
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from tools import TOOL_SCHEMAS, run_tool

try:
    import anthropic
except ImportError:  # pragma: no cover
    print("Missing dependency. Run: pip install -r requirements.txt", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parent
DEFAULT_LEADS = ROOT / "sample_leads.json"
MAX_TURNS = 8
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

SYSTEM_PROMPT = """You are a lead intake agent for a solo AI workflow / automation consultant.

Your job for each inbound lead:
1. Qualify the lead (Hot / Warm / Cold / Spam) using budget signals, urgency, fit, and specificity.
2. Always create a CRM record so nothing is lost.
3. For Hot or strong Warm leads: notify the owner and draft a first follow-up email.
4. For spam, scams, bots, or highly ambiguous cases: flag for human review and do NOT draft an email.
5. Prefer safe escalation over aggressive outreach when unsure.

Rules:
- Use tools to take action. Do not pretend a tool ran.
- Do not invent contact details.
- Keep drafts short, human, and non-hype.
- When finished acting, give a brief final summary of what you did and why.
"""


def load_leads(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Leads file must be a JSON array")
    return data


def format_lead_message(lead: dict[str, Any]) -> str:
    return (
        "Process this inbound lead end to end.\n\n"
        f"Name: {lead.get('name', '')}\n"
        f"Email: {lead.get('email', '')}\n"
        f"Company: {lead.get('company', '')}\n"
        f"Source: {lead.get('source', 'unknown')}\n"
        f"Inquiry:\n{lead.get('inquiry', '')}\n"
    )


def _content_block_to_dict(block: Any) -> dict[str, Any]:
    """Normalize SDK content blocks to plain dicts for the next request."""
    btype = getattr(block, "type", None) or block.get("type")
    if btype == "text":
        text = getattr(block, "text", None) or block.get("text", "")
        return {"type": "text", "text": text}
    if btype == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", None) or block.get("id"),
            "name": getattr(block, "name", None) or block.get("name"),
            "input": getattr(block, "input", None) or block.get("input", {}),
        }
    # Fallback: best-effort
    if hasattr(block, "model_dump"):
        return block.model_dump()
    return dict(block)


def process_lead(client: anthropic.Anthropic, lead: dict[str, Any]) -> dict[str, Any]:
    lead_id = lead.get("id", lead.get("email", "unknown"))
    print("\n" + "=" * 64)
    print(f"LEAD: {lead_id} — {lead.get('name', '')}")
    print("=" * 64)

    messages: list[dict[str, Any]] = [
        {"role": "user", "content": format_lead_message(lead)}
    ]
    tool_calls: list[dict[str, Any]] = []
    final_text = ""

    for turn in range(1, MAX_TURNS + 1):
        print(f"\n--- turn {turn}/{MAX_TURNS} ---")
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=messages,
        )

        assistant_content = [_content_block_to_dict(b) for b in response.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_uses = [b for b in assistant_content if b.get("type") == "tool_use"]
        texts = [b.get("text", "") for b in assistant_content if b.get("type") == "text"]
        for t in texts:
            if t.strip():
                print(f"[assistant] {t.strip()}")
                final_text = t.strip()

        if response.stop_reason == "end_turn" or not tool_uses:
            break

        tool_results: list[dict[str, Any]] = []
        for use in tool_uses:
            name = use["name"]
            tool_input = use.get("input") or {}
            print(f"[tool call] {name}({json.dumps(tool_input, ensure_ascii=False)})")
            result = run_tool(name, tool_input)
            print(f"[tool result] {json.dumps(result, ensure_ascii=False)}")
            tool_calls.append({"name": name, "input": tool_input, "result": result})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": use["id"],
                    "content": json.dumps(result),
                }
            )

        messages.append({"role": "user", "content": tool_results})
    else:
        print(f"[safety] Hit turn limit ({MAX_TURNS}); stopping.")

    return {
        "lead_id": lead_id,
        "tool_calls": tool_calls,
        "tools_used": [c["name"] for c in tool_calls],
        "final_text": final_text,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Lead Intake Agent")
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_LEADS,
        help="Path to JSON array of leads",
    )
    parser.add_argument(
        "--lead",
        type=str,
        default=None,
        help="Run a single sample lead by id (e.g. hot, warm, spam)",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "ANTHROPIC_API_KEY is not set.\n"
            "  export ANTHROPIC_API_KEY=sk-ant-...\n"
            "  # or copy .env.example → .env and load it",
            file=sys.stderr,
        )
        return 1

    leads = load_leads(args.file)
    if args.lead:
        leads = [lead for lead in leads if lead.get("id") == args.lead]
        if not leads:
            print(f"No lead with id={args.lead!r} in {args.file}", file=sys.stderr)
            return 1

    client = anthropic.Anthropic(api_key=api_key)
    summaries = []
    for lead in leads:
        summaries.append(process_lead(client, lead))

    print("\n" + "=" * 64)
    print("RUN SUMMARY")
    print("=" * 64)
    for s in summaries:
        print(f"- {s['lead_id']}: tools={s['tools_used']}")

    out_path = ROOT / "data" / "last_run_summary.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summaries, f, indent=2)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
