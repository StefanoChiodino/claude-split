"""Validation: cycle detection, status recomputation, full board validation."""

from .board import (
    MILESTONE_ID_RE,
    TICKET_ID_RE,
    VALID_BOARD_STATUSES,
    VALID_MILESTONE_STATUSES,
    VALID_TICKET_STATUSES,
    find_ticket,
    get_all_tickets,
)


def has_cycle(tickets: list[dict], new_ticket_id: str, new_deps: list[str]) -> bool:
    graph = {}
    for t in tickets:
        graph[t["id"]] = list(t.get("depends_on", []))
    if new_ticket_id:
        graph[new_ticket_id] = list(new_deps)

    visited = set()
    in_stack = set()

    def dfs(node):
        if node in in_stack:
            return True
        if node in visited:
            return False
        visited.add(node)
        in_stack.add(node)
        for dep in graph.get(node, []):
            if dfs(dep):
                return True
        in_stack.discard(node)
        return False

    for node in graph:
        if dfs(node):
            return True
    return False


def recompute_ticket_blocked_statuses(board: dict) -> None:
    all_tickets = get_all_tickets(board)
    ticket_map = {t["id"]: t for t in all_tickets}

    for t in all_tickets:
        if t["status"] in ("done", "in_progress", "pending_approval", "skipped"):
            continue
        deps = t.get("depends_on", [])
        if not deps:
            if t["status"] in ("blocked", "blocked_by_skip"):
                t["status"] = "backlog"
            continue

        dep_statuses = [ticket_map[d]["status"] for d in deps if d in ticket_map]
        all_done = all(s == "done" for s in dep_statuses)
        any_skipped = any(s == "skipped" for s in dep_statuses)
        all_resolved = all(s in ("done", "skipped") for s in dep_statuses)

        if all_done:
            if t["status"] in ("blocked", "blocked_by_skip"):
                t["status"] = "backlog"
        elif any_skipped and all_resolved:
            t["status"] = "blocked_by_skip"
        elif t["status"] not in ("blocked", "blocked_by_skip"):
            t["status"] = "blocked"


def recompute_milestone_statuses(board: dict) -> None:
    found_incomplete = False
    for ms in board.get("milestones", []):
        ms_tickets = ms.get("tickets", [])
        all_done = ms_tickets and all(t.get("status") in ("done", "skipped") for t in ms_tickets)
        if all_done:
            ms["status"] = "done"
        elif not found_incomplete:
            ms["status"] = "in_progress" if ms_tickets else "todo"
            found_incomplete = True
        else:
            ms["status"] = "todo"


def validate_board(board: dict) -> list[str]:
    errors = []
    all_tickets = get_all_tickets(board)
    ticket_ids = {t["id"] for t in all_tickets}

    for field in ("spec", "title", "created", "status"):
        if field not in board:
            errors.append(f"Missing board field: {field}")

    if board.get("status") not in VALID_BOARD_STATUSES:
        errors.append(f"Invalid board status: {board.get('status')}")

    for t in all_tickets:
        tid = t.get("id", "?")
        for field in ("id", "title", "persona", "status", "depends_on", "acceptance_criteria", "produces"):
            if field not in t:
                errors.append(f"Ticket {tid}: missing field '{field}'")
        if t.get("status") not in VALID_TICKET_STATUSES:
            errors.append(f"Ticket {tid}: invalid status '{t.get('status')}'")
        if t.get("id") and not TICKET_ID_RE.match(t["id"]):
            errors.append(f"Ticket {tid}: invalid ID format")

    for t in all_tickets:
        tid = t.get("id", "?")
        for dep in t.get("depends_on", []):
            if dep not in ticket_ids:
                errors.append(f"Ticket {tid}: dependency '{dep}' not found")
        if t.get("created_by") and t["created_by"] not in ticket_ids:
            errors.append(f"Ticket {tid}: created_by '{t['created_by']}' not found")
        if t.get("created_by"):
            parent = find_ticket(board, t["created_by"])
            if parent and tid not in parent.get("follow_ups", []):
                errors.append(f"Ticket {tid}: created_by '{t['created_by']}' but parent doesn't list {tid} in follow_ups")
        for fu in t.get("follow_ups", []):
            child = find_ticket(board, fu)
            if not child:
                errors.append(f"Ticket {tid}: follow_up '{fu}' not found")
            elif child.get("created_by") != tid:
                errors.append(f"Ticket {tid}: follow_up '{fu}' doesn't have created_by = {tid}")

    if has_cycle(all_tickets, "", []):
        errors.append("Dependency cycle detected")

    for t in all_tickets:
        tid = t.get("id", "?")
        if t.get("status") == "done":
            if not t.get("artifacts"):
                errors.append(f"Ticket {tid}: done but no artifacts")

    for ms in board.get("milestones", []):
        if not MILESTONE_ID_RE.match(ms.get("id", "")):
            errors.append(f"Milestone {ms.get('id', '?')}: invalid ID format")
        if ms.get("status") not in VALID_MILESTONE_STATUSES:
            errors.append(f"Milestone {ms.get('id', '?')}: invalid status '{ms.get('status')}'")

    return errors
