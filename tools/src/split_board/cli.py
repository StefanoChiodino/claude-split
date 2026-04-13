"""CLI entry point: argparse setup and main()."""

import argparse
import sys

from .board import DEFAULT_BASE_DIR, VALID_TICKET_STATUSES
from .commands import (
    cmd_dashboard,
    cmd_decision_add,
    cmd_followup_create,
    cmd_milestone_add,
    cmd_milestone_move_ticket,
    cmd_spec_abandon,
    cmd_spec_archive,
    cmd_spec_init,
    cmd_spec_list,
    cmd_status,
    cmd_ticket_add,
    cmd_ticket_add_dependency,
    cmd_ticket_remove_dependency,
    cmd_ticket_update,
    cmd_validate,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="split-board",
        description="Split Board CLI — manage board state for Split specs",
    )
    parser.add_argument(
        "--base-dir",
        default=DEFAULT_BASE_DIR,
        help=f"Base directory for split data (default: {DEFAULT_BASE_DIR})",
    )
    sub = parser.add_subparsers(dest="command")

    # spec
    spec_parser = sub.add_parser("spec", help="Spec lifecycle commands")
    spec_sub = spec_parser.add_subparsers(dest="spec_command")

    init_p = spec_sub.add_parser("init", help="Initialize a new spec")
    init_p.add_argument("--title", required=True)
    init_p.set_defaults(func=cmd_spec_init)

    list_p = spec_sub.add_parser("list", help="List specs")
    list_p.add_argument("--status", choices=("active", "archived", "abandoned"))
    list_p.set_defaults(func=cmd_spec_list)

    archive_p = spec_sub.add_parser("archive", help="Archive a spec")
    archive_p.add_argument("--spec", required=True)
    archive_p.set_defaults(func=cmd_spec_archive)

    abandon_p = spec_sub.add_parser("abandon", help="Abandon a spec")
    abandon_p.add_argument("--spec", required=True)
    abandon_p.set_defaults(func=cmd_spec_abandon)

    # milestone
    ms_parser = sub.add_parser("milestone", help="Milestone commands")
    ms_sub = ms_parser.add_subparsers(dest="milestone_command")

    ms_add_p = ms_sub.add_parser("add", help="Add a milestone")
    ms_add_p.add_argument("--title", required=True)
    ms_add_p.add_argument("--spec")
    ms_add_p.set_defaults(func=cmd_milestone_add)

    ms_move_p = ms_sub.add_parser("move-ticket", help="Move a ticket to a milestone")
    ms_move_p.add_argument("--ticket", required=True)
    ms_move_p.add_argument("--milestone", required=True)
    ms_move_p.add_argument("--spec")
    ms_move_p.set_defaults(func=cmd_milestone_move_ticket)

    # ticket
    tk_parser = sub.add_parser("ticket", help="Ticket commands")
    tk_sub = tk_parser.add_subparsers(dest="ticket_command")

    tk_add_p = tk_sub.add_parser("add", help="Add a ticket")
    tk_add_p.add_argument("--title", required=True)
    tk_add_p.add_argument("--persona", required=True)
    tk_add_p.add_argument("--acceptance-criteria", required=True)
    tk_add_p.add_argument("--produces", required=True)
    tk_add_p.add_argument("--milestone", required=True)
    tk_add_p.add_argument("--depends-on")
    tk_add_p.add_argument("--requires-approval", action="store_true", default=False)
    tk_add_p.add_argument("--spec")
    tk_add_p.set_defaults(func=cmd_ticket_add)

    tk_update_p = tk_sub.add_parser("update", help="Update a ticket")
    tk_update_p.add_argument("--id", required=True)
    tk_update_p.add_argument("--status", choices=VALID_TICKET_STATUSES)
    tk_update_p.add_argument("--tokens-used", type=int)
    tk_update_p.add_argument("--artifact", action="append", dest="artifacts")
    tk_update_p.add_argument("--persona")
    tk_update_p.add_argument("--spec")
    tk_update_p.set_defaults(func=cmd_ticket_update)

    tk_add_dep_p = tk_sub.add_parser("add-dependency", help="Add a dependency")
    tk_add_dep_p.add_argument("--id", required=True)
    tk_add_dep_p.add_argument("--depends-on", required=True)
    tk_add_dep_p.add_argument("--spec")
    tk_add_dep_p.set_defaults(func=cmd_ticket_add_dependency)

    tk_rm_dep_p = tk_sub.add_parser("remove-dependency", help="Remove a dependency")
    tk_rm_dep_p.add_argument("--id", required=True)
    tk_rm_dep_p.add_argument("--depends-on", required=True)
    tk_rm_dep_p.add_argument("--spec")
    tk_rm_dep_p.set_defaults(func=cmd_ticket_remove_dependency)

    # followup
    fu_parser = sub.add_parser("followup", help="Follow-up ticket commands")
    fu_sub = fu_parser.add_subparsers(dest="followup_command")

    fu_create_p = fu_sub.add_parser("create", help="Create a follow-up ticket")
    fu_create_p.add_argument("--parent", required=True)
    fu_create_p.add_argument("--persona", required=True)
    fu_create_p.add_argument("--title", required=True)
    fu_create_p.add_argument("--acceptance-criteria", required=True)
    fu_create_p.add_argument("--produces", required=True)
    fu_create_p.add_argument("--spec")
    fu_create_p.set_defaults(func=cmd_followup_create)

    # decision
    dec_parser = sub.add_parser("decision", help="Decision commands")
    dec_sub = dec_parser.add_subparsers(dest="decision_command")

    dec_add_p = dec_sub.add_parser("add", help="Record a decision")
    dec_add_p.add_argument("--ticket", required=True)
    dec_add_p.add_argument("--question", required=True)
    dec_add_p.add_argument("--answered-by", required=True)
    dec_add_p.add_argument("--answer", required=True)
    dec_add_p.add_argument("--spec")
    dec_add_p.set_defaults(func=cmd_decision_add)

    # dashboard
    dashboard_p = sub.add_parser("dashboard", help="Live dashboard TUI")
    dashboard_p.add_argument("--spec")
    dashboard_p.set_defaults(func=cmd_dashboard)

    # status
    status_p = sub.add_parser("status", help="Show board status")
    status_p.add_argument("--spec")
    status_p.set_defaults(func=cmd_status)

    # validate
    validate_p = sub.add_parser("validate", help="Validate board integrity")
    validate_p.add_argument("--spec")
    validate_p.set_defaults(func=cmd_validate)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)
