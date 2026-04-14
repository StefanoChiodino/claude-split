"""Command handlers for all split-board subcommands."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from .board import (
    VALID_TRANSITIONS,
    append_log,
    error,
    find_ticket,
    find_ticket_milestone,
    get_all_tickets,
    load_board,
    next_followup_id,
    next_milestone_id,
    next_spec_id,
    next_ticket_id,
    now_iso,
    resolve_spec_dir,
    save_board,
    slugify,
    success,
)
from .validation import (
    has_cycle,
    recompute_milestone_statuses,
    recompute_ticket_blocked_statuses,
    validate_board,
)


# --- Spec ---

def cmd_spec_init(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    active_dir = base_dir / "active"
    active_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "archive").mkdir(parents=True, exist_ok=True)

    spec_id = next_spec_id(base_dir)
    slug = slugify(args.title)
    dir_name = f"{spec_id}-{slug}" if slug else spec_id
    spec_dir = active_dir / dir_name

    spec_dir.mkdir()
    (spec_dir / "artifacts").mkdir()
    (spec_dir / "log.md").write_text("")
    (spec_dir / "spec.md").write_text("")

    board = {
        "spec": spec_id,
        "title": args.title,
        "created": now_iso(),
        "status": "active",
        "milestones": [],
    }

    save_board(board, spec_dir / "board.yaml")
    append_log(spec_dir, f'{spec_id} created: "{args.title}"')
    success(f"Spec {spec_id} created at {spec_dir}")


def cmd_spec_list(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    specs = []
    for subdir, default_status in [("active", "active"), ("archive", None)]:
        d = base_dir / subdir
        if not d.exists():
            continue
        for name in sorted(d.iterdir()):
            board_path = name / "board.yaml"
            if board_path.exists():
                board = load_board(board_path)
                status = board.get("status", default_status or "unknown")
                specs.append((board.get("spec", name.name), board.get("title", ""), status))

    if args.status:
        specs = [(s, t, st) for s, t, st in specs if st == args.status]

    if not specs:
        print("No specs found.")
        return
    for spec_id, title, status in specs:
        print(f"  {spec_id}: \"{title}\" [{status}]")


def cmd_spec_archive(args: argparse.Namespace) -> None:
    _move_spec(args, "archived")


def cmd_spec_abandon(args: argparse.Namespace) -> None:
    _move_spec(args, "abandoned")


def _move_spec(args: argparse.Namespace, new_status: str) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, args.spec)
    archive_dir = base_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)
    board["status"] = new_status
    save_board(board, board_path)
    append_log(spec_dir, f"{board.get('spec', spec_dir.name)} {new_status}")

    dest = archive_dir / spec_dir.name
    shutil.move(str(spec_dir), str(dest))
    success(f"Spec {board.get('spec', spec_dir.name)} {new_status} → {dest}")


# --- Milestone ---

def cmd_milestone_add(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    ms_id = next_milestone_id(board)
    milestone = {
        "id": ms_id,
        "title": args.title,
        "status": "todo",
        "tickets": [],
    }
    board["milestones"].append(milestone)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    append_log(spec_dir, f'{ms_id} added: "{args.title}"')
    success(f"Milestone {ms_id} added to {board['spec']}")


def cmd_milestone_move_ticket(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    target_ms = None
    for ms in board["milestones"]:
        if ms["id"] == args.milestone:
            target_ms = ms
            break
    if not target_ms:
        error(f"Milestone {args.milestone} not found")

    ticket = None
    for ms in board["milestones"]:
        for i, t in enumerate(ms["tickets"]):
            if t["id"] == args.ticket:
                ticket = ms["tickets"].pop(i)
                break
        if ticket:
            break
    if not ticket:
        error(f"Ticket {args.ticket} not found")

    target_ms["tickets"].append(ticket)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    append_log(spec_dir, f"{args.ticket} moved to {args.milestone}")
    success(f"Ticket {args.ticket} moved to milestone {args.milestone}")


# --- Ticket ---

def cmd_ticket_add(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    ticket_id = next_ticket_id(board)
    deps = [d.strip() for d in args.depends_on.split(",")] if args.depends_on else []

    all_tickets = get_all_tickets(board)
    all_ids = {t["id"] for t in all_tickets}
    for dep in deps:
        if dep not in all_ids:
            error(f"Dependency {dep} not found\n  Available tickets: {', '.join(sorted(all_ids)) if all_ids else '(none)'}")

    if deps and has_cycle(all_tickets, ticket_id, deps):
        error(f"Adding dependencies {deps} to {ticket_id} would create a cycle")

    status = "blocked" if deps else "backlog"

    ticket = {
        "id": ticket_id,
        "title": args.title,
        "persona": args.persona,
        "status": status,
        "depends_on": deps,
        "acceptance_criteria": args.acceptance_criteria,
        "produces": args.produces,
        "requires_approval": args.requires_approval,
        "artifacts": [],
        "follow_ups": [],
        "created_by": None,
        "decisions": [],
    }

    if not args.milestone:
        error("--milestone is required\n  Available milestones: " + ", ".join(ms["id"] for ms in board.get("milestones", [])))

    placed = False
    for ms in board["milestones"]:
        if ms["id"] == args.milestone:
            ms["tickets"].append(ticket)
            placed = True
            break
    if not placed:
        error(f"Milestone {args.milestone} not found")

    recompute_milestone_statuses(board)
    save_board(board, board_path)
    append_log(spec_dir, f'{ticket_id} added to {args.milestone}: "{args.title}" @{args.persona}')
    success(f"Ticket {ticket_id} added to {board['spec']} (milestone {args.milestone})")


def cmd_ticket_update(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    ticket = find_ticket(board, args.id)
    if not ticket:
        error(f"Ticket {args.id} not found")

    old_status = ticket["status"]

    if args.status:
        new_status = args.status

        if new_status not in VALID_TRANSITIONS.get(old_status, set()):
            error(
                f"Cannot transition {args.id} from '{old_status}' to '{new_status}'\n"
                f"  Valid transitions from '{old_status}': {', '.join(sorted(VALID_TRANSITIONS[old_status])) or '(none)'}"
            )

        if new_status == "in_progress":
            all_tickets = get_all_tickets(board)
            ticket_map = {t["id"]: t for t in all_tickets}
            for dep_id in ticket.get("depends_on", []):
                dep = ticket_map.get(dep_id)
                if dep and dep["status"] != "done":
                    error(
                        f"Cannot set {args.id} to in_progress\n"
                        f"  Reason: Dependency {dep_id} has status '{dep['status']}' (must be 'done')\n"
                        f"  Fix: Complete {dep_id} first:\n"
                        f"    split-board ticket update --id {dep_id} --status done --artifact <path>\n"
                        f"  Or remove the dependency:\n"
                        f"    split-board ticket remove-dependency --id {args.id} --depends-on {dep_id}"
                    )

        if new_status in ("done", "pending_approval"):
            artifacts = list(ticket.get("artifacts", []))
            if args.artifacts:
                artifacts.extend(args.artifacts)
            if not artifacts:
                error(
                    f"Cannot set {args.id} to {new_status}\n"
                    f"  Reason: At least one artifact is required\n"
                    f"  Fix: split-board ticket update --id {args.id} --status {new_status} --artifact <path>"
                )

        if new_status == "pending_approval" and not ticket.get("requires_approval"):
            error(
                f"Cannot set {args.id} to pending_approval\n"
                f"  Reason: Ticket does not have requires_approval set"
            )

        ticket["status"] = new_status

    if args.artifacts:
        for a in args.artifacts:
            if a not in ticket["artifacts"]:
                ticket["artifacts"].append(a)
    if args.persona:
        ticket["persona"] = args.persona

    # Build log message from all changes
    parts = [args.id]
    if args.status:
        parts.append(f"{old_status}→{args.status} @{ticket['persona']}")
    if args.artifacts:
        for a in args.artifacts:
            parts.append(f"artifact: {a}")

    recompute_ticket_blocked_statuses(board)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    if len(parts) > 1:
        append_log(spec_dir, " ".join(parts))
    success(f"Ticket {args.id} updated")


def cmd_ticket_add_dependency(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    ticket = find_ticket(board, args.id)
    if not ticket:
        error(f"Ticket {args.id} not found")
    dep_ticket = find_ticket(board, args.depends_on)
    if not dep_ticket:
        error(f"Dependency ticket {args.depends_on} not found")
    if args.depends_on in ticket.get("depends_on", []):
        error(f"{args.id} already depends on {args.depends_on}")

    new_deps = list(ticket.get("depends_on", [])) + [args.depends_on]
    if has_cycle(get_all_tickets(board), args.id, new_deps):
        error(
            f"Adding dependency {args.depends_on} to {args.id} would create a cycle\n"
            f"  {args.depends_on} already depends (directly or indirectly) on {args.id}"
        )

    ticket["depends_on"] = new_deps
    recompute_ticket_blocked_statuses(board)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    append_log(spec_dir, f"{args.id} dependency added: {args.depends_on}")
    success(f"Dependency {args.depends_on} added to {args.id}")


def cmd_ticket_remove_dependency(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    ticket = find_ticket(board, args.id)
    if not ticket:
        error(f"Ticket {args.id} not found")
    if args.depends_on not in ticket.get("depends_on", []):
        error(f"{args.id} does not depend on {args.depends_on}")

    ticket["depends_on"].remove(args.depends_on)
    recompute_ticket_blocked_statuses(board)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    success(f"Dependency {args.depends_on} removed from {args.id}")


# --- Follow-up ---

def cmd_followup_create(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    parent = find_ticket(board, args.parent)
    if not parent:
        error(f"Parent ticket {args.parent} not found")

    if parent.get("created_by"):
        error(
            f"Cannot create follow-up of {args.parent}\n"
            f"  Reason: {args.parent} is already a follow-up of {parent['created_by']}. Two-level limit reached."
        )

    followup_id = next_followup_id(board, args.parent)

    ticket = {
        "id": followup_id,
        "title": args.title,
        "persona": args.persona,
        "status": "blocked",
        "depends_on": [args.parent],
        "acceptance_criteria": args.acceptance_criteria,
        "produces": args.produces,
        "requires_approval": False,
        "artifacts": [],
        "follow_ups": [],
        "created_by": args.parent,
        "decisions": [],
    }

    ms = find_ticket_milestone(board, args.parent)
    if ms:
        ms["tickets"].append(ticket)
    else:
        error(f"Parent ticket {args.parent} not found in any milestone")

    parent["follow_ups"].append(followup_id)

    recompute_ticket_blocked_statuses(board)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    append_log(spec_dir, f'{followup_id} follow-up of {args.parent}: "{args.title}" @{args.persona}')
    success(f"Follow-up {followup_id} created for {args.parent}")


# --- Decision ---

def cmd_decision_add(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    ticket = find_ticket(board, args.ticket)
    if not ticket:
        error(f"Ticket {args.ticket} not found")

    decision = {
        "question": args.question,
        "answered_by": args.answered_by,
        "answer": args.answer,
        "timestamp": now_iso(),
    }
    ticket["decisions"].append(decision)

    save_board(board, board_path)
    append_log(spec_dir, f'{args.ticket} decision by {args.answered_by}: "{args.question}"')
    success(f"Decision recorded on {args.ticket}")


# --- Log ---

def cmd_log(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    append_log(spec_dir, args.message)
    success("Log entry added")


# --- Status & Validate ---

def cmd_status(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    metrics_path = spec_dir / "metrics.yaml"
    metrics = yaml.safe_load(metrics_path.read_text()) if metrics_path.exists() else {}

    print(f"=== {board['spec']}: {board['title']} [{board['status']}] ===")
    print()

    for ms in board.get("milestones", []):
        ms_tickets = ms.get("tickets", [])
        done_count = sum(1 for t in ms_tickets if t["status"] == "done")
        print(f"  {ms['id']}: {ms['title']} [{ms['status']}] [{done_count}/{len(ms_tickets)} done]")
        for t in ms_tickets:
            _print_ticket(t)
        print()

    if metrics:
        print(f"Tickets: {metrics.get('completed_tickets', 0)}/{metrics.get('total_tickets', 0)} done | "
              f"Tokens: {metrics.get('total_tokens', 0)} | "
              f"Follow-ups: {metrics.get('follow_up_tickets', 0)} | "
              f"Questions: {metrics.get('user_questions', 0)}")


def _print_ticket(t: dict) -> None:
    deps = f" (depends: {', '.join(t['depends_on'])})" if t.get("depends_on") else ""
    approval = " [NEEDS APPROVAL]" if t.get("requires_approval") and t["status"] == "pending_approval" else ""
    print(f"    {t['id']}: [{t['status']}] {t['title']} @{t['persona']}{deps}{approval}")


# --- Dashboard ---

def cmd_dashboard(args: argparse.Namespace) -> None:
    uv = shutil.which("uv")
    if not uv:
        error(
            "uv is required for the dashboard.\n"
            "  Install: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
            "  See: https://docs.astral.sh/uv/"
        )

    script = Path(__file__).parent.parent.parent / "split" / "tools" / "split_board_dashboard.py"
    if not script.exists():
        error(f"Dashboard script not found at {script}")

    cmd = [uv, "run", str(script), "--base-dir", str(args.base_dir)]
    if args.spec:
        cmd.extend(["--spec", args.spec])

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def cmd_validate(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)

    errors = validate_board(board)
    if errors:
        print(f"Validation found {len(errors)} issue(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    else:
        from .board import success
        success(f"Board {board['spec']} is valid")
