"""Board state: YAML I/O, ticket helpers, ID generation, metrics."""

import datetime
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

import yaml


class BoardError(Exception):
    """Raised for board-level errors instead of calling sys.exit."""

# --- Constants ---

VALID_TICKET_STATUSES = (
    "backlog", "blocked", "in_progress", "pending_approval",
    "done", "skipped", "blocked_by_skip",
)
VALID_MILESTONE_STATUSES = ("todo", "in_progress", "done")
VALID_BOARD_STATUSES = ("active", "completed", "archived", "abandoned")

SPEC_ID_RE = re.compile(r"^S(\d{3})$")
MILESTONE_ID_RE = re.compile(r"^M(\d{3})$")
TICKET_ID_RE = re.compile(r"^T(\d{3})([a-z])?$")

DEFAULT_BASE_DIR = ".claude/split"

VALID_TRANSITIONS = {
    "backlog": {"in_progress", "skipped"},
    "blocked": {"skipped"},
    "in_progress": {"done", "pending_approval", "backlog", "skipped"},
    "pending_approval": {"done", "in_progress", "skipped"},
    "done": set(),
    "skipped": set(),
    "blocked_by_skip": {"skipped"},
}


# --- Output ---

def error(msg: str) -> NoReturn:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise BoardError(msg)


def success(msg: str) -> None:
    print(f"OK: {msg}")


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def append_log(spec_dir: Path, message: str) -> None:
    log_path = spec_dir / "log.md"
    with open(log_path, "a") as f:
        f.write(f"{now_iso()} {message}\n")


def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug[:40].rstrip("-")


# --- YAML I/O ---

def load_board(board_path: Path) -> dict:
    with open(board_path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        error(f"Board file is empty or corrupt: {board_path}")
    return data


def _atomic_write(path: Path, content: str) -> None:
    dir_ = path.parent
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as f:
        f.write(content)
        tmp_path = f.name
    os.replace(tmp_path, path)


def save_board(board: dict, board_path: Path) -> None:
    _atomic_write(board_path, yaml.dump(board, default_flow_style=False, sort_keys=False))
    metrics = compute_metrics(board)
    metrics_path = board_path.parent / "metrics.yaml"
    _atomic_write(metrics_path, yaml.dump(metrics, default_flow_style=False, sort_keys=False))


# --- Ticket Helpers ---

def get_all_tickets(board: dict) -> list[dict]:
    tickets = []
    for ms in board.get("milestones", []):
        tickets.extend(ms.get("tickets", []))
    return tickets


def find_ticket(board: dict, ticket_id: str) -> dict | None:
    for t in get_all_tickets(board):
        if t["id"] == ticket_id:
            return t
    return None


def find_ticket_milestone(board: dict, ticket_id: str) -> dict | None:
    for ms in board.get("milestones", []):
        for t in ms.get("tickets", []):
            if t["id"] == ticket_id:
                return ms
    return None


# --- Metrics ---

def compute_metrics(board: dict) -> dict:
    tickets = get_all_tickets(board)
    milestones = board.get("milestones", [])
    resolved_tickets = sum(
        1 for t in tickets if t.get("status") in ("done", "skipped")
    )

    user_questions = 0
    for t in tickets:
        for d in t.get("decisions", []):
            if d.get("answered_by") == "user":
                user_questions += 1

    milestones_completed = 0
    for ms in milestones:
        ms_tickets = ms.get("tickets", [])
        if ms_tickets and all(t.get("status") in ("done", "skipped") for t in ms_tickets):
            milestones_completed += 1

    return {
        "started": board.get("created"),
        "agent_dispatches": sum(
            1 for t in tickets
            if t.get("status") in ("in_progress", "pending_approval", "done")
        ),
        "total_tickets": len(tickets),
        "completed_tickets": sum(1 for t in tickets if t.get("status") == "done"),
        "resolved_tickets": resolved_tickets,
        "follow_up_tickets": sum(1 for t in tickets if t.get("created_by")),
        "user_questions": user_questions,
        "milestones_completed": milestones_completed,
    }


# --- ID Generation ---

def next_spec_id(base_dir: Path) -> str:
    existing = set()
    for subdir in ("active", "archive"):
        d = base_dir / subdir
        if d.exists():
            for name in os.listdir(d):
                match = re.match(r"^S(\d{3})", name)
                if match:
                    existing.add(int(match.group(1)))
    n = 1
    while n in existing:
        n += 1
    return f"S{n:03d}"


def next_milestone_id(board: dict) -> str:
    existing = set()
    for ms in board.get("milestones", []):
        match = MILESTONE_ID_RE.match(ms["id"])
        if match:
            existing.add(int(match.group(1)))
    n = 1
    while n in existing:
        n += 1
    return f"M{n:03d}"


def next_ticket_id(board: dict) -> str:
    existing = set()
    for t in get_all_tickets(board):
        match = TICKET_ID_RE.match(t["id"])
        if match:
            existing.add(int(match.group(1)))
    n = 1
    while n in existing:
        n += 1
    return f"T{n:03d}"


def next_followup_id(board: dict, parent_id: str) -> str:
    match = TICKET_ID_RE.match(parent_id)
    if not match:
        error(f"Invalid parent ticket ID: {parent_id}")
    base_num = match.group(1)
    existing_suffixes = set()
    for t in get_all_tickets(board):
        t_match = TICKET_ID_RE.match(t["id"])
        if t_match and t_match.group(1) == base_num and t_match.group(2):
            existing_suffixes.add(t_match.group(2))
    for c in "abcdefghijklmnopqrstuvwxyz":
        if c not in existing_suffixes:
            return f"T{base_num}{c}"
    error(f"Exhausted follow-up IDs for {parent_id}")


# --- Spec Resolution ---

def resolve_spec_dir(base_dir: Path, spec_arg: str | None, require: bool = True) -> Path | None:
    active_dir = base_dir / "active"
    if not active_dir.exists():
        if require:
            error("No active specs. Create one with:\n  split-board spec init --title <title>")
        return None

    active_specs = []
    for name in sorted(os.listdir(active_dir)):
        if (active_dir / name).is_dir():
            active_specs.append(name)

    if spec_arg:
        for name in active_specs:
            if name == spec_arg or name.startswith(spec_arg + "-"):
                return active_dir / name
        archive_dir = base_dir / "archive"
        if archive_dir.exists():
            for name in sorted(os.listdir(archive_dir)):
                if name == spec_arg or name.startswith(spec_arg + "-"):
                    return archive_dir / name
        error(f"Spec '{spec_arg}' not found")

    if len(active_specs) == 0:
        if require:
            error("No active specs. Create one with:\n  split-board spec init --title <title>")
        return None
    elif len(active_specs) == 1:
        return active_dir / active_specs[0]
    else:
        lines = ["Multiple active specs. Specify one with --spec:"]
        for name in active_specs:
            board_path = active_dir / name / "board.yaml"
            if board_path.exists():
                board = load_board(board_path)
                lines.append(f"  {name}: \"{board.get('title', '?')}\" (created {board.get('created', '?')})")
            else:
                lines.append(f"  {name}")
        error("\n".join(lines))
