#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "textual>=1.0",
#   "pyyaml>=6.0",
# ]
# ///
"""Split Board Dashboard — live Textual TUI for monitoring board state."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from rich import box
from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer
from textual.widgets import Footer, Static

# --- Status-to-column mapping ---

COLUMN_INDEX = {
    "backlog": 0,
    "blocked": 0,
    "blocked_by_skip": 0,
    "in_progress": 1,
    "pending_approval": 2,
    "done": 3,
    "skipped": 3,
}

COLUMNS = [
    ("\u25cb", "BACKLOG", "dim"),
    ("\u25cf", "ACTIVE", "bold white"),
    ("\u23f8", "APPROVAL", "bold yellow"),
    ("\u2713", "DONE", "bold green"),
]

TICKET_STYLE = {
    "backlog": "dim",
    "blocked": "dim italic",
    "blocked_by_skip": "dim red",
    "in_progress": "white",
    "pending_approval": "yellow",
    "done": "green",
    "skipped": "red",
}


# --- Helpers ---



def safe_load(path: Path) -> dict | None:
    try:
        return yaml.safe_load(path.read_text())
    except Exception:
        return None


def tail_lines(path: Path, n: int = 10) -> list[str]:
    try:
        text = path.read_text().strip()
        return text.splitlines()[-n:] if text else []
    except Exception:
        return []


# --- Renderers ---


def ticket_card(t: dict) -> Text:
    """Render a single ticket card as Rich Text."""
    style = TICKET_STYLE.get(t.get("status", ""), "")
    ticket_id = t["id"]

    result = Text(style=style)
    result.append(ticket_id, style="bold underline")

    rest = [t.get("persona", ""), t.get("title", "")]
    result.append("\n" + "\n".join(rest))
    if t.get("status") == "pending_approval":
        result.append("\n\u26a0 NEEDS YOU", style="bold yellow blink")
    return result


def milestone_table(ms: dict) -> Table:
    """Render one milestone as a Rich Table with 4 kanban columns."""
    tickets = ms.get("tickets", [])
    done = sum(1 for t in tickets if t.get("status") == "done")

    # Bucket tickets into columns
    cols: list[list[dict]] = [[] for _ in range(4)]
    for t in tickets:
        cols[COLUMN_INDEX.get(t.get("status", ""), 0)].append(t)

    tbl = Table(
        show_header=True,
        expand=True,
        box=box.ROUNDED,
        title=f"{ms['id']}: {ms['title']}  [{done}/{len(tickets)} done]",
        title_style="bold",
        padding=(0, 1),
    )
    for icon, label, style in COLUMNS:
        tbl.add_column(f"{icon} {label}", header_style=style, ratio=1, no_wrap=False)

    max_rows = max((len(c) for c in cols), default=0) or 1
    for r in range(max_rows):
        row = []
        for c in cols:
            row.append(ticket_card(c[r]) if r < len(c) else Text(""))
        tbl.add_row(*row)

    return tbl


def board_view(board: dict) -> RenderableType:
    """Full kanban view — one table per milestone."""
    milestones = board.get("milestones", [])
    if not milestones:
        return Text("  No milestones.", style="dim")

    parts: list[RenderableType] = []
    for ms in milestones:
        parts.append(milestone_table(ms))
        parts.append(Text(""))
    return Group(*parts)


def activity_view(lines: list[str]) -> RenderableType:
    if not lines:
        return Text("  No activity yet.", style="dim")
    return Group(*(Text(f"  {line}") for line in reversed(lines)))


def metrics_view(board: dict, log_mtime: float = 0) -> RenderableType:
    tickets = []
    for ms in board.get("milestones", []):
        tickets.extend(ms.get("tickets", []))
    milestones = board.get("milestones", [])

    done_tickets = sum(1 for t in tickets if t.get("status") == "done")
    dispatches = sum(
        1 for t in tickets
        if t.get("status") in ("in_progress", "pending_approval", "done")
    )
    follow_ups = sum(1 for t in tickets if t.get("created_by"))
    user_qs = sum(
        1 for t in tickets
        for d in t.get("decisions", [])
        if d.get("answered_by") == "user"
    )
    ms_done = sum(
        1 for ms in milestones
        if ms.get("tickets")
        and all(t.get("status") == "done" for t in ms["tickets"])
    )
    # Line 1
    line1 = Text("  ")
    line1.append(f"Tickets: {done_tickets}/{len(tickets)} done", style="bold")
    line1.append("  \u2502  ")
    line1.append(f"Dispatches: {dispatches}", style="bold")
    line1.append("  \u2502  ")
    line1.append(f"Follow-ups: {follow_ups}", style="bold")
    line1.append("  \u2502  ")
    line1.append(f"Questions: {user_qs}", style="bold")

    # Line 2
    line2 = Text("  ")
    line2.append(f"Milestones: {ms_done}/{len(milestones)}", style="bold")

    created = board.get("created")
    if created:
        try:
            start = datetime.fromisoformat(created)
            elapsed = datetime.now(timezone.utc) - start
            mins = max(0, int(elapsed.total_seconds() / 60))
            el = f"{mins // 60}h{mins % 60}m" if mins >= 60 else f"{mins}m"
            line2.append("  \u2502  ")
            line2.append(f"Elapsed: {el}", style="bold")
        except (ValueError, TypeError):
            pass

    if log_mtime > 0:
        ago_secs = datetime.now().timestamp() - log_mtime
        ago_mins = int(ago_secs / 60)
        if ago_mins < 1:
            ago_str = "just now"
        elif ago_mins < 60:
            ago_str = f"{ago_mins}m ago"
        else:
            ago_str = f"{ago_mins // 60}h{ago_mins % 60}m ago"
        line2.append("  \u2502  ")
        line2.append(f"Last activity: {ago_str}", style="bold")

    return Group(line1, line2)


# --- Textual App ---


class DashboardApp(App):
    TITLE = "Split Board"

    CSS = """
    Screen {
        layout: vertical;
    }
    #spec-header {
        height: auto;
        max-height: 2;
        background: $primary;
        color: $text;
        padding: 0 1;
    }
    #board-scroll {
        height: 1fr;
    }
    #board-content {
        padding: 0 1;
    }
    #activity-header {
        height: 1;
        padding: 0 1;
    }
    #activity-body {
        height: auto;
        max-height: 8;
        padding: 0 1;
    }
    #metrics-header {
        height: 1;
        padding: 0 1;
    }
    #metrics-body {
        height: auto;
        max-height: 3;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "cycle_spec", "Cycle spec"),
    ]

    def __init__(self, base_dir: Path, spec_filter: str | None = None):
        super().__init__()
        self.base_dir = base_dir
        self.spec_filter = spec_filter
        self.specs: list[Path] = []
        self.spec_idx = 0
        self._board_mtime = 0.0
        self._log_mtime = 0.0

    def compose(self) -> ComposeResult:
        yield Static(id="spec-header")
        with ScrollableContainer(id="board-scroll"):
            yield Static(id="board-content")
        yield Static(id="activity-header")
        yield Static(id="activity-body")
        yield Static(id="metrics-header")
        yield Static(id="metrics-body")
        yield Footer()

    def on_mount(self) -> None:
        self._find_specs()
        self._refresh()
        self.set_interval(1.0, self._poll)

    def _find_specs(self) -> None:
        active = self.base_dir / "active"
        if not active.is_dir():
            self.specs = []
            return
        found = []
        for name in sorted(os.listdir(active)):
            d = active / name
            if d.is_dir() and (d / "board.yaml").exists():
                if (
                    self.spec_filter is None
                    or name == self.spec_filter
                    or name.startswith(self.spec_filter + "-")
                ):
                    found.append(d)
        self.specs = found
        if self.spec_idx >= len(found):
            self.spec_idx = 0

    @property
    def _spec_dir(self) -> Path | None:
        return self.specs[self.spec_idx] if self.specs else None

    def _poll(self) -> None:
        # Re-discover specs in case new ones appeared
        self._find_specs()

        sd = self._spec_dir
        if not sd:
            self._refresh()
            return

        bp = sd / "board.yaml"
        lp = sd / "log.md"
        bm = bp.stat().st_mtime if bp.exists() else 0.0
        lm = lp.stat().st_mtime if lp.exists() else 0.0
        if bm != self._board_mtime or lm != self._log_mtime:
            self._refresh()

    def _refresh(self) -> None:
        sd = self._spec_dir
        if not sd:
            self.query_one("#spec-header").update(
                Text(" No active specs found.", style="bold red")
            )
            for wid in (
                "#board-content",
                "#activity-header",
                "#activity-body",
                "#metrics-header",
                "#metrics-body",
            ):
                self.query_one(wid).update("")
            return

        bp = sd / "board.yaml"
        lp = sd / "log.md"
        self._board_mtime = bp.stat().st_mtime if bp.exists() else 0.0
        self._log_mtime = lp.stat().st_mtime if lp.exists() else 0.0

        board = safe_load(bp)
        if not board:
            self.query_one("#spec-header").update(
                Text(" Error loading board.", style="bold red")
            )
            return

        # Header
        self.query_one("#spec-header").update(self._header(board))

        # Board
        self.query_one("#board-content").update(board_view(board))

        # Activity
        ah = Text("\u2500\u2500 Activity ", style="bold")
        ah.append("\u2500" * 70, style="dim")
        self.query_one("#activity-header").update(ah)
        self.query_one("#activity-body").update(activity_view(tail_lines(lp)))

        # Metrics
        mh = Text("\u2500\u2500 Metrics ", style="bold")
        mh.append("\u2500" * 70, style="dim")
        self.query_one("#metrics-header").update(mh)
        self.query_one("#metrics-body").update(
            metrics_view(board, self._log_mtime)
        )

    def _header(self, board: dict) -> Text:
        if len(self.specs) > 1:
            t = Text(" ")
            for i, sd in enumerate(self.specs):
                b = safe_load(sd / "board.yaml")
                label = b.get("spec", sd.name) if b else sd.name
                if i == self.spec_idx:
                    t.append(f"[{label}]", style="bold reverse")
                else:
                    t.append(f" {label} ", style="dim")
                t.append(" ")
            t.append(f"\u2500\u2500 {board.get('title', '?')}", style="bold")
            return t
        spec_id = board.get("spec", "?")
        return Text(
            f" {spec_id} \u2500\u2500 {board.get('title', '?')}", style="bold"
        )

    def action_cycle_spec(self) -> None:
        if len(self.specs) > 1:
            self.spec_idx = (self.spec_idx + 1) % len(self.specs)
            self._board_mtime = 0.0
            self._log_mtime = 0.0
            self._refresh()


def main() -> None:
    parser = argparse.ArgumentParser(description="Split Board Dashboard")
    parser.add_argument("--base-dir", default=".claude/split")
    parser.add_argument("--spec", default=None)
    args = parser.parse_args()

    DashboardApp(base_dir=Path(args.base_dir), spec_filter=args.spec).run()


if __name__ == "__main__":
    main()
