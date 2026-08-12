"""
Local-first tool implementations for the Lead Intake Agent.

Each tool mirrors a real integration (Airtable, Slack/email, Gmail) so the
agent loop stays the same when you swap local JSON files for live APIs.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent / "data"
CRM_PATH = DATA_DIR / "crm_records.json"
NOTIFICATIONS_PATH = DATA_DIR / "notifications.json"
DRAFTS_PATH = DATA_DIR / "draft_emails.json"
FLAGS_PATH = DATA_DIR / "human_flags.json"


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save_list(path: Path, items: list[dict[str, Any]]) -> None:
    _ensure_data_dir()
    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Tool schemas (Anthropic tool-use format) ---------------------------------

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "create_crm_record",
        "description": (
            "Create a CRM lead record. Always call this for any inbound lead "
            "so there is an audit trail, including spam and low-quality leads."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Lead full name"},
                "email": {"type": "string", "description": "Lead email address"},
                "company": {"type": "string", "description": "Company name if known"},
                "inquiry": {"type": "string", "description": "Original inquiry text"},
                "priority": {
                    "type": "string",
                    "enum": ["Hot", "Warm", "Cold", "Spam"],
                    "description": "Qualification label",
                },
                "score": {
                    "type": "integer",
                    "description": "Lead score 0-100 (use 0-10 for spam)",
                },
                "summary": {
                    "type": "string",
                    "description": "One or two sentence summary of the lead",
                },
                "service_interest": {
                    "type": "string",
                    "description": "Inferred service interest category",
                },
            },
            "required": [
                "name",
                "email",
                "inquiry",
                "priority",
                "score",
                "summary",
            ],
        },
    },
    {
        "name": "notify_owner",
        "description": (
            "Alert the business owner about a lead that needs immediate attention. "
            "Use for Hot leads or escalations. Do not use for clear spam."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_name": {"type": "string"},
                "priority": {"type": "string"},
                "score": {"type": "integer"},
                "reason": {
                    "type": "string",
                    "description": "Why the owner should care right now",
                },
                "channel": {
                    "type": "string",
                    "enum": ["email", "slack"],
                    "description": "Notification channel",
                },
            },
            "required": ["lead_name", "priority", "score", "reason"],
        },
    },
    {
        "name": "draft_followup_email",
        "description": (
            "Draft a first-reply email to a legitimate lead. "
            "Do NOT draft emails for spam, bots, or abusive inquiries."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "to_email": {"type": "string"},
                "to_name": {"type": "string"},
                "subject": {"type": "string"},
                "body": {
                    "type": "string",
                    "description": "Friendly, professional reply draft (3-6 sentences)",
                },
            },
            "required": ["to_email", "to_name", "subject", "body"],
        },
    },
    {
        "name": "flag_for_human",
        "description": (
            "Escalate for human review when the lead is spam, ambiguous, risky, "
            "or outside the normal offer. Prefer this over drafting an email when unsure."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "lead_name": {"type": "string"},
                "lead_email": {"type": "string"},
                "reason": {
                    "type": "string",
                    "description": "Why a human should review this lead",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "required": ["lead_name", "lead_email", "reason"],
        },
    },
]


# --- Tool implementations -----------------------------------------------------


def create_crm_record(
    name: str,
    email: str,
    inquiry: str,
    priority: str,
    score: int,
    summary: str,
    company: str = "",
    service_interest: str = "Other",
) -> dict[str, Any]:
    records = _load_list(CRM_PATH)
    record = {
        "id": f"lead_{uuid.uuid4().hex[:8]}",
        "created_at": _now(),
        "name": name,
        "email": email,
        "company": company or "",
        "inquiry": inquiry,
        "priority": priority,
        "score": int(score),
        "summary": summary,
        "service_interest": service_interest or "Other",
        "status": "New",
    }
    records.append(record)
    _save_list(CRM_PATH, records)
    return {"ok": True, "record": record}


def notify_owner(
    lead_name: str,
    priority: str,
    score: int,
    reason: str,
    channel: str = "email",
) -> dict[str, Any]:
    notes = _load_list(NOTIFICATIONS_PATH)
    note = {
        "id": f"notify_{uuid.uuid4().hex[:8]}",
        "created_at": _now(),
        "channel": channel or "email",
        "lead_name": lead_name,
        "priority": priority,
        "score": int(score),
        "reason": reason,
        "status": "queued_local",
    }
    notes.append(note)
    _save_list(NOTIFICATIONS_PATH, notes)
    return {"ok": True, "notification": note}


def draft_followup_email(
    to_email: str,
    to_name: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    drafts = _load_list(DRAFTS_PATH)
    draft = {
        "id": f"draft_{uuid.uuid4().hex[:8]}",
        "created_at": _now(),
        "to_email": to_email,
        "to_name": to_name,
        "subject": subject,
        "body": body,
        "status": "draft_only",
    }
    drafts.append(draft)
    _save_list(DRAFTS_PATH, drafts)
    return {"ok": True, "draft": draft}


def flag_for_human(
    lead_name: str,
    lead_email: str,
    reason: str,
    urgency: str = "medium",
) -> dict[str, Any]:
    flags = _load_list(FLAGS_PATH)
    flag = {
        "id": f"flag_{uuid.uuid4().hex[:8]}",
        "created_at": _now(),
        "lead_name": lead_name,
        "lead_email": lead_email,
        "reason": reason,
        "urgency": urgency or "medium",
        "status": "needs_review",
    }
    flags.append(flag)
    _save_list(FLAGS_PATH, flags)
    return {"ok": True, "flag": flag}


TOOL_HANDLERS = {
    "create_crm_record": create_crm_record,
    "notify_owner": notify_owner,
    "draft_followup_email": draft_followup_email,
    "flag_for_human": flag_for_human,
}


def run_tool(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOL_HANDLERS:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        return TOOL_HANDLERS[name](**tool_input)
    except TypeError as exc:
        return {"ok": False, "error": f"Invalid tool input for {name}: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surface tool errors to the agent
        return {"ok": False, "error": str(exc)}
