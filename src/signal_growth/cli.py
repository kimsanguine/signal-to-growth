"""Command line interface for validation and safe workflow routing."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from .adapters import (
    ChannelTalkAdapter,
    KakaoOpenBuilderAdapter,
    NaverTalkTalkAdapter,
)
from .append_only import AppendOnlyError, append_record
from .channel_contracts import RequestContext
from .connector_validation import validate_connector_directory
from .contracts import validate_artifact_directory
from .integrations import (
    IntegrationContractError,
    build_hplan_intake,
    import_pmf_radar,
    write_json,
)
from .policy import fixture_ingest_policy
from .privacy import scan_path
from .questions import lint_questions
from .repo_validation import validate_repository
from .workflow import completed_skills, next_skill, next_skill_reason


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
    # This command normalizes repository fixtures, which carry no provider
    # authentication, so the fixture-only policy relaxation is explicit for
    # every adapter it constructs.
    adapters = {
        "naver-talktalk": NaverTalkTalkAdapter(
            _PUBLIC_DUMMY_HMAC_KEY,
            policy=fixture_ingest_policy(),
        ),
        "channel-talk": ChannelTalkAdapter(
            _PUBLIC_DUMMY_HMAC_KEY,
            policy=fixture_ingest_policy(),
        ),
        "kakao-openbuilder": KakaoOpenBuilderAdapter(
            _PUBLIC_DUMMY_HMAC_KEY,
            policy=fixture_ingest_policy(),
        ),
    }
    adapter = adapters[args.provider]
    headers = {}
    if args.request_id is not None:
        headers["X-Request-Id"] = args.request_id
    event = adapter.ingest(
        raw_body,
        headers=headers,
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


def command_append_record(args: argparse.Namespace) -> int:
    try:
        record = json.loads(args.record)
    except json.JSONDecodeError as exc:
        print(f"--record is not valid JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(record, dict):
        print("--record must be a JSON object.", file=sys.stderr)
        return 1
    try:
        line_count = append_record(args.path.resolve(), record)
    except AppendOnlyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Appended 1 line to {args.path} ({line_count} lines total).")
    return 0


def command_next_step(args: argparse.Namespace) -> int:
    directory = args.directory.resolve()
    payload = {
        "completed_skills": completed_skills(directory),
        "next_skill": next_skill(directory, objective=args.objective),
        "reason": next_skill_reason(directory, objective=args.objective),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_import_pmf_radar(args: argparse.Namespace) -> int:
    try:
        report = import_pmf_radar(
            args.input.resolve(),
            output_directory=(
                args.output_directory.resolve()
                if args.output_directory is not None
                else None
            ),
            write=args.write,
            force=args.force,
        )
    except (OSError, IntegrationContractError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_export_hplan(args: argparse.Namespace) -> int:
    try:
        brief = build_hplan_intake(
            args.artifacts.resolve(),
            decision_id=args.decision_id,
            product_name=args.product_name,
            jtbd=args.jtbd,
            functional_requirements=args.functional_requirement or (),
            cogs_ceiling=args.cogs_ceiling,
            latency_budget=args.latency_budget,
            counter_position=args.counter_position,
            mvp_slice=args.mvp_slice,
        )
        if args.require_ready and brief["status"] != "ready_for_gate_review":
            print(
                "hplan intake is not ready; unknown fields: "
                + ", ".join(brief["unknown_fields"]),
                file=sys.stderr,
            )
            return 1
        if args.output is not None:
            write_json(brief, args.output.resolve(), force=args.force)
        else:
            print(json.dumps(brief, ensure_ascii=False, indent=2))
    except (OSError, ValueError, IntegrationContractError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
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
        choices=("naver-talktalk", "channel-talk", "kakao-openbuilder"),
    )
    normalize_event.add_argument("--input", required=True, type=Path)
    normalize_event.add_argument("--received-at")
    normalize_event.add_argument(
        "--request-id",
        help="Required X-Request-Id value for kakao-openbuilder fixtures.",
    )
    normalize_event.add_argument("--output", type=Path)
    normalize_event.set_defaults(func=command_normalize_event)

    scan_privacy = subparsers.add_parser("scan-privacy")
    scan_privacy.add_argument("path", type=Path)
    scan_privacy.set_defaults(func=command_scan_privacy)

    lint_questions_parser = subparsers.add_parser("lint-questions")
    lint_questions_parser.add_argument("path", type=Path)
    lint_questions_parser.set_defaults(func=command_lint_questions)

    append_record_parser = subparsers.add_parser("append-record")
    append_record_parser.add_argument("path", type=Path)
    append_record_parser.add_argument("record", help="A single JSON object.")
    append_record_parser.set_defaults(func=command_append_record)

    next_step = subparsers.add_parser("next-step")
    next_step.add_argument("directory", type=Path)
    next_step.add_argument("--objective")
    next_step.set_defaults(func=command_next_step)

    import_pmf = subparsers.add_parser("import-pmf-radar")
    import_pmf.add_argument("--input", required=True, type=Path)
    import_pmf.add_argument("--output-directory", type=Path)
    import_pmf.add_argument(
        "--write",
        action="store_true",
        help="Materialize validated artifacts. The default is a dry run.",
    )
    import_pmf.add_argument("--force", action="store_true")
    import_pmf.set_defaults(func=command_import_pmf_radar)

    export_hplan = subparsers.add_parser("export-hplan")
    export_hplan.add_argument("--artifacts", required=True, type=Path)
    export_hplan.add_argument("--decision-id")
    export_hplan.add_argument("--product-name")
    export_hplan.add_argument("--jtbd")
    export_hplan.add_argument(
        "--functional-requirement",
        action="append",
    )
    export_hplan.add_argument("--cogs-ceiling")
    export_hplan.add_argument("--latency-budget")
    export_hplan.add_argument("--counter-position")
    export_hplan.add_argument("--mvp-slice")
    export_hplan.add_argument("--output", type=Path)
    export_hplan.add_argument("--require-ready", action="store_true")
    export_hplan.add_argument("--force", action="store_true")
    export_hplan.set_defaults(func=command_export_hplan)

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
