"""Command line interface for validation and safe workflow routing."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .adapters import ChannelTalkAdapter, NaverTalkTalkAdapter
from .channel_contracts import RequestContext
from .connector_validation import validate_connector_directory
from .contracts import render_issues, validate_artifact_directory
from .privacy import scan_path
from .questions import lint_questions
from .repo_validation import validate_repository
from .workflow import completed_skills, next_skill


_PUBLIC_DUMMY_HMAC_KEY = b"signal-to-growth-public-dummy"


def _print_validation(issues: list[object], success: str) -> int:
    if issues:
        for issue in issues:
            render = getattr(issue, "render", None)
            print(render() if callable(render) else str(issue), file=sys.stderr)
        return 1
    print(success)
    return 0


def command_validate_repo(args: argparse.Namespace) -> int:
    return _print_validation(
        validate_repository(args.root.resolve()),
        "Repository structure is valid.",
    )


def command_validate_artifacts(args: argparse.Namespace) -> int:
    return _print_validation(
        validate_artifact_directory(
            args.directory.resolve(),
            require_complete=args.require_complete,
        ),
        "Artifact contracts are valid.",
    )


def command_validate_connectors(args: argparse.Namespace) -> int:
    return _print_validation(
        validate_connector_directory(
            args.directory.resolve(),
            require_complete=args.require_complete,
        ),
        "Connector artifacts are valid.",
    )


def command_normalize_event(args: argparse.Namespace) -> int:
    raw_body = args.input.resolve().read_bytes()
    received_at = args.received_at or datetime.now(UTC).isoformat()
    adapter = (
        NaverTalkTalkAdapter(_PUBLIC_DUMMY_HMAC_KEY)
        if args.provider == "naver-talktalk"
        else ChannelTalkAdapter(_PUBLIC_DUMMY_HMAC_KEY)
    )
    event = adapter.ingest(
        raw_body,
        received_at=received_at,
        request_context=RequestContext(environment="fixture"),
    )
    rendered = json.dumps(event.to_dict(), ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        args.output.resolve().write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


def command_scan_privacy(args: argparse.Namespace) -> int:
    findings = scan_path(args.path.resolve())
    if findings:
        for finding in findings:
            print(finding.render(args.path), file=sys.stderr)
        return 1
    print("No supported private-data pattern detected.")
    return 0


def command_lint_questions(args: argparse.Namespace) -> int:
    text = args.path.read_text(encoding="utf-8")
    issues = lint_questions(text)
    return _print_validation(issues, "No configured interview-question risk detected.")


def command_next_step(args: argparse.Namespace) -> int:
    directory = args.directory.resolve()
    payload = {
        "completed_skills": completed_skills(directory),
        "next_skill": next_skill(directory),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_demo(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    repo_issues = validate_repository(root)
    artifact_issues = validate_artifact_directory(
        root / "fixtures" / "public-dummy" / "artifacts",
        require_complete=True,
    )
    connector_issues = validate_connector_directory(
        root / "fixtures" / "public-dummy" / "connector-artifacts",
        require_complete=True,
    )
    privacy_findings = scan_path(
        root / "fixtures" / "public-dummy" / "interviews" / "P-20260725-001.md"
    )
    if repo_issues or artifact_issues or connector_issues or privacy_findings:
        for issue in repo_issues + artifact_issues + connector_issues:
            print(issue.render(), file=sys.stderr)
        for finding in privacy_findings:
            print(finding.render(root), file=sys.stderr)
        return 1
    print("Demo validation passed: repository, contracts, references, and privacy.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="signal-to-growth",
        description="Validate evidence-to-growth artifacts and route the next safe step.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_repo = subparsers.add_parser("validate-repo")
    validate_repo.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    validate_repo.set_defaults(func=command_validate_repo)

    validate_artifacts = subparsers.add_parser("validate-artifacts")
    validate_artifacts.add_argument("directory", type=Path)
    validate_artifacts.add_argument("--require-complete", action="store_true")
    validate_artifacts.set_defaults(func=command_validate_artifacts)

    validate_connectors = subparsers.add_parser("validate-connectors")
    validate_connectors.add_argument("directory", type=Path)
    validate_connectors.add_argument("--require-complete", action="store_true")
    validate_connectors.set_defaults(func=command_validate_connectors)

    normalize_event = subparsers.add_parser("normalize-event")
    normalize_event.add_argument(
        "--provider",
        required=True,
        choices=("naver-talktalk", "channel-talk"),
    )
    normalize_event.add_argument("--input", required=True, type=Path)
    normalize_event.add_argument("--received-at")
    normalize_event.add_argument("--output", type=Path)
    normalize_event.set_defaults(func=command_normalize_event)

    scan_privacy = subparsers.add_parser("scan-privacy")
    scan_privacy.add_argument("path", type=Path)
    scan_privacy.set_defaults(func=command_scan_privacy)

    lint_questions_parser = subparsers.add_parser("lint-questions")
    lint_questions_parser.add_argument("path", type=Path)
    lint_questions_parser.set_defaults(func=command_lint_questions)

    next_step = subparsers.add_parser("next-step")
    next_step.add_argument("directory", type=Path)
    next_step.set_defaults(func=command_next_step)

    demo = subparsers.add_parser("demo")
    demo.add_argument("root", type=Path, nargs="?", default=Path.cwd())
    demo.set_defaults(func=command_demo)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
