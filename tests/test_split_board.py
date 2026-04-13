import subprocess
import sys
import os

import pytest
import yaml

from split_board.cli import main
from split_board.board import slugify, append_log


# --- Helpers ---

def _init_spec(tmp_path, title="Test"):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", title])
    spec_dir = list((tmp_path / "active").iterdir())[0]
    return tmp_path, spec_dir


def _init_spec_with_milestone(tmp_path, title="Test", milestone_title="M1"):
    base, spec_dir = _init_spec(tmp_path, title)
    main(["--base-dir", str(base), "milestone", "add", "--title", milestone_title])
    return base, spec_dir


def _load(spec_dir):
    return yaml.safe_load((spec_dir / "board.yaml").read_text())


def _metrics(spec_dir):
    return yaml.safe_load((spec_dir / "metrics.yaml").read_text())


# --- Slugify ---

def test_slugify_basic():
    assert slugify("Rate Limiting") == "rate-limiting"


def test_slugify_special_chars():
    assert slugify("Hello, World! (v2)") == "hello-world-v2"


def test_slugify_collapse_hyphens():
    assert slugify("too---many---hyphens") == "too-many-hyphens"


def test_slugify_truncate():
    result = slugify("a" * 60)
    assert len(result) <= 40


def test_slugify_strip_trailing_hyphen():
    assert slugify("trailing-") == "trailing"


# --- Spec Lifecycle ---

def test_spec_init(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Rate limiting"])
    dirs = list((tmp_path / "active").iterdir())
    assert len(dirs) == 1
    spec_dir = dirs[0]
    assert spec_dir.name == "S001-rate-limiting"
    board = _load(spec_dir)
    assert board["spec"] == "S001"
    assert board["title"] == "Rate limiting"
    assert board["status"] == "active"
    assert board["milestones"] == []
    assert "complexity" not in board
    metrics = _metrics(spec_dir)
    assert metrics["total_tickets"] == 0
    assert (spec_dir / "log.md").exists()
    assert (spec_dir / "artifacts").is_dir()
    assert (spec_dir / "spec.md").exists()


def test_spec_init_auto_increments_id(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "First"])
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Second"])
    names = sorted(d.name for d in (tmp_path / "active").iterdir())
    assert names[0].startswith("S001")
    assert names[1].startswith("S002")


def test_spec_list(tmp_path, capsys):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Alpha"])
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Beta"])
    main(["--base-dir", str(tmp_path), "spec", "list"])
    out = capsys.readouterr().out
    assert "S001" in out and "Alpha" in out
    assert "S002" in out and "Beta" in out


def test_spec_archive(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "To archive"])
    main(["--base-dir", str(tmp_path), "spec", "archive", "--spec", "S001"])
    assert not (tmp_path / "active" / "S001-to-archive").exists()
    archived_dir = tmp_path / "archive" / "S001-to-archive"
    assert archived_dir.exists()
    board = _load(archived_dir)
    assert board["status"] == "archived"


def test_spec_abandon(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "To abandon"])
    main(["--base-dir", str(tmp_path), "spec", "abandon", "--spec", "S001"])
    archived_dir = tmp_path / "archive" / "S001-to-abandon"
    assert archived_dir.exists()
    board = _load(archived_dir)
    assert board["status"] == "abandoned"


# --- Milestones ---

def test_milestone_add(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "Design & core"])
    board = _load(spec_dir)
    assert len(board["milestones"]) == 1
    assert board["milestones"][0]["id"] == "M001"
    assert board["milestones"][0]["title"] == "Design & core"
    assert board["milestones"][0]["tickets"] == []


def test_milestone_add_auto_increments(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "First"])
    main(["--base-dir", str(base), "milestone", "add", "--title", "Second"])
    board = _load(spec_dir)
    assert board["milestones"][0]["id"] == "M001"
    assert board["milestones"][1]["id"] == "M002"


def test_milestone_move_ticket(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "M1"])
    main(["--base-dir", str(base), "milestone", "add", "--title", "M2"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "T", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "milestone", "move-ticket", "--ticket", "T001", "--milestone", "M002"])
    board = _load(spec_dir)
    assert len(board["milestones"][0]["tickets"]) == 0
    assert len(board["milestones"][1]["tickets"]) == 1
    assert board["milestones"][1]["tickets"][0]["id"] == "T001"


# --- Tickets ---

def test_ticket_add(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Do thing", "--persona", "dev", "--acceptance-criteria", "it works", "--produces", "impl", "--milestone", "M001"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert len(tickets) == 1
    t = tickets[0]
    assert t["id"] == "T001"
    assert t["title"] == "Do thing"
    assert t["persona"] == "dev"
    assert t["status"] == "backlog"
    assert t["depends_on"] == []
    assert t["requires_approval"] is False
    assert t["tokens_used"] == 0
    assert t["artifacts"] == []
    assert t["follow_ups"] == []
    assert t["created_by"] is None
    assert t["decisions"] == []


def test_ticket_add_with_dependency_sets_blocked(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert tickets[1]["status"] == "blocked"
    assert tickets[1]["depends_on"] == ["T001"]


def test_ticket_add_rejects_missing_dependency(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "ticket", "add", "--title", "X", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T999"])


def test_ticket_add_requires_approval_flag(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Risky", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--requires-approval"])
    board = _load(spec_dir)
    assert board["milestones"][0]["tickets"][0]["requires_approval"] is True


# --- Ticket Update ---

def test_ticket_update_to_in_progress(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    board = _load(spec_dir)
    assert board["milestones"][0]["tickets"][0]["status"] == "in_progress"


def test_ticket_update_to_done_requires_tokens_and_artifact(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done"])


def test_ticket_update_to_done_with_tokens_and_artifact(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "5000", "--artifact", "out.md"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert tickets[0]["status"] == "done"
    assert tickets[0]["tokens_used"] == 5000
    assert "out.md" in tickets[0]["artifacts"]


def test_ticket_update_in_progress_requires_deps_done(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "ticket", "update", "--id", "T002", "--status", "in_progress"])


def test_ticket_update_auto_unblocks_downstream(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    assert _load(spec_dir)["milestones"][0]["tickets"][1]["status"] == "blocked"
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "100", "--artifact", "a.md"])
    board = _load(spec_dir)
    assert board["milestones"][0]["tickets"][1]["status"] == "backlog"


def test_ticket_update_pending_approval(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Risky", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--requires-approval"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "pending_approval", "--tokens-used", "100", "--artifact", "a.md"])
    board = _load(spec_dir)
    assert board["milestones"][0]["tickets"][0]["status"] == "pending_approval"


def test_ticket_update_pending_approval_requires_flag(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Normal", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "pending_approval", "--tokens-used", "100", "--artifact", "a.md"])


def test_ticket_update_retry_back_to_backlog(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "backlog"])
    board = _load(spec_dir)
    assert board["milestones"][0]["tickets"][0]["status"] == "backlog"


def test_ticket_update_skip_cascades_blocked_by_skip(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "skipped"])
    board = _load(spec_dir)
    assert board["milestones"][0]["tickets"][1]["status"] == "blocked_by_skip"


# --- Dependencies ---

def test_ticket_add_dependency(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add-dependency", "--id", "T002", "--depends-on", "T001"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert "T001" in tickets[1]["depends_on"]
    assert tickets[1]["status"] == "blocked"


def test_ticket_add_dependency_rejects_cycle(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "ticket", "add-dependency", "--id", "T001", "--depends-on", "T002"])


def test_ticket_remove_dependency(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    main(["--base-dir", str(base), "ticket", "remove-dependency", "--id", "T002", "--depends-on", "T001"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert tickets[1]["depends_on"] == []
    assert tickets[1]["status"] == "backlog"


# --- Follow-ups ---

def test_followup_create(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Parent", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "dev", "--title", "Fix bug", "--acceptance-criteria", "no bugs", "--produces", "impl"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert len(tickets) == 2
    followup = tickets[1]
    assert followup["id"] == "T001a"
    assert followup["created_by"] == "T001"
    assert "T001" in followup["depends_on"]
    assert "T001a" in tickets[0]["follow_ups"]


def test_followup_auto_increments_suffix(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Parent", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "dev", "--title", "Fix A", "--acceptance-criteria", "ac", "--produces", "impl"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "dev", "--title", "Fix B", "--acceptance-criteria", "ac", "--produces", "impl"])
    board = _load(spec_dir)
    tickets = board["milestones"][0]["tickets"]
    assert tickets[1]["id"] == "T001a"
    assert tickets[2]["id"] == "T001b"


def test_followup_two_level_limit(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Root", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "dev", "--title", "Child", "--acceptance-criteria", "ac", "--produces", "impl"])
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "followup", "create", "--parent", "T001a", "--persona", "dev", "--title", "Grandchild", "--acceptance-criteria", "ac", "--produces", "impl"])


def test_followup_in_same_milestone(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Parent", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "dev", "--title", "Fix", "--acceptance-criteria", "ac", "--produces", "impl"])
    board = _load(spec_dir)
    assert len(board["milestones"][0]["tickets"]) == 2
    assert board["milestones"][0]["tickets"][1]["id"] == "T001a"


# --- Decisions ---

def test_decision_add(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "decision", "add", "--ticket", "T001", "--question", "Redis or memory?", "--answered-by", "user", "--answer", "Redis"])
    board = _load(spec_dir)
    decisions = board["milestones"][0]["tickets"][0]["decisions"]
    assert len(decisions) == 1
    assert decisions[0]["question"] == "Redis or memory?"
    assert decisions[0]["answered_by"] == "user"
    assert decisions[0]["answer"] == "Redis"
    assert "timestamp" in decisions[0]


def test_decision_counted_in_metrics(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "decision", "add", "--ticket", "T001", "--question", "Q1", "--answered-by", "user", "--answer", "A1"])
    main(["--base-dir", str(base), "decision", "add", "--ticket", "T001", "--question", "Q2", "--answered-by", "tech-lead", "--answer", "A2"])
    metrics = _metrics(spec_dir)
    assert metrics["user_questions"] == 1


# --- Status & Validate ---

def test_status_with_milestones(tmp_path, capsys):
    base, _ = _init_spec_with_milestone(tmp_path, milestone_title="Phase 1")
    main(["--base-dir", str(base), "ticket", "add", "--title", "Design", "--persona", "tl", "--acceptance-criteria", "ac", "--produces", "doc", "--milestone", "M001"])
    main(["--base-dir", str(base), "status"])
    out = capsys.readouterr().out
    assert "S001" in out
    assert "M001" in out and "Phase 1" in out and "Design" in out


def test_validate_clean_board(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "validate"])


def test_validate_catches_missing_artifact_on_done(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    board = _load(spec_dir)
    board["milestones"][0]["tickets"][0]["status"] = "done"
    board["milestones"][0]["tickets"][0]["tokens_used"] = 100
    with open(spec_dir / "board.yaml", "w") as f:
        yaml.dump(board, f, default_flow_style=False, sort_keys=False)
    with pytest.raises(SystemExit):
        main(["--base-dir", str(base), "validate"])


# --- Metrics ---

def test_metrics_through_full_workflow(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "5000", "--artifact", "a.md"])
    main(["--base-dir", str(base), "decision", "add", "--ticket", "T001", "--question", "Q", "--answered-by", "user", "--answer", "A"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "dev", "--title", "Fix", "--acceptance-criteria", "ac", "--produces", "impl"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T002", "--status", "in_progress"])

    metrics = _metrics(spec_dir)
    assert metrics["total_tickets"] == 3
    assert metrics["completed_tickets"] == 1
    assert metrics["follow_up_tickets"] == 1
    assert metrics["user_questions"] == 1
    assert metrics["total_tokens"] == 5000
    assert metrics["agent_dispatches"] >= 2


# --- Spec Disambiguation ---

def test_spec_disambiguation_single(tmp_path):
    base, _ = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "X", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])


def test_spec_disambiguation_multiple_requires_spec(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Alpha"])
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Beta"])
    with pytest.raises(SystemExit):
        main(["--base-dir", str(tmp_path), "milestone", "add", "--title", "M1"])


def test_spec_disambiguation_with_spec_flag(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Alpha"])
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Beta"])
    main(["--base-dir", str(tmp_path), "milestone", "add", "--title", "M1", "--spec", "S002"])
    main(["--base-dir", str(tmp_path), "ticket", "add", "--title", "X", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--spec", "S002"])
    spec_dir = tmp_path / "active" / "S002-beta"
    board = _load(spec_dir)
    assert len(board["milestones"][0]["tickets"]) == 1


# --- Milestone Statuses ---

def test_milestone_status_auto_computed(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "M1"])
    main(["--base-dir", str(base), "milestone", "add", "--title", "M2"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M002"])
    board = _load(spec_dir)
    assert board["milestones"][0]["status"] == "in_progress"
    assert board["milestones"][1]["status"] == "todo"
    # Complete M1
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "100", "--artifact", "a.md"])
    board = _load(spec_dir)
    assert board["milestones"][0]["status"] == "done"
    assert board["milestones"][1]["status"] == "in_progress"


# --- append_log ---

def test_append_log_creates_entry(tmp_path):
    log_path = tmp_path / "log.md"
    log_path.write_text("")
    append_log(tmp_path, "T001 backlog→in_progress @dev")
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    # ISO timestamp + space + message
    assert lines[0].endswith("T001 backlog→in_progress @dev")
    assert "T" in lines[0][:30]  # has ISO timestamp prefix


def test_append_log_accumulates(tmp_path):
    log_path = tmp_path / "log.md"
    log_path.write_text("")
    append_log(tmp_path, "first")
    append_log(tmp_path, "second")
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("first")
    assert lines[1].endswith("second")


# --- Smoke Tests ---

def test_smoke_help():
    result = subprocess.run(
        [sys.executable, "-m", "split_board", "--help"],
        capture_output=True, text=True,
        cwd=os.path.join(os.path.dirname(__file__), ".."),
    )
    assert result.returncode == 0
    assert "split-board" in result.stdout


def test_smoke_spec_init_and_status(tmp_path):
    project_root = os.path.join(os.path.dirname(__file__), "..")
    result = subprocess.run(
        [sys.executable, "-m", "split_board", "--base-dir", str(tmp_path), "spec", "init", "--title", "Smoke"],
        capture_output=True, text=True,
        cwd=project_root,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout

    result = subprocess.run(
        [sys.executable, "-m", "split_board", "--base-dir", str(tmp_path), "status"],
        capture_output=True, text=True,
        cwd=project_root,
    )
    assert result.returncode == 0
    assert "Smoke" in result.stdout
