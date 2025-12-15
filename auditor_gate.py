#!/usr/bin/env python3
"""
Git/CI gate for Auditor.

This script is designed to be invoked from Git hooks (pre-commit, commit-msg, pre-push)
and from CI to provide a deterministic "allow/deny" decision based on the existing
AuditorEngine rules.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


REPO_ROOT_ENV = "AUDITOR_REPO_ROOT"
BOOTSTRAP_MAX_COMMITS_ENV = "AUDITOR_PRE_PUSH_BOOTSTRAP_MAX_COMMITS"


@dataclass(frozen=True)
class Violation:
    rule_name: str
    severity: str
    action: str
    description: str
    location: str
    suggestion: str | None


def _run_git(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=check,
    )


def _repo_root() -> Path:
    if REPO_ROOT_ENV in os.environ and os.environ[REPO_ROOT_ENV]:
        return Path(os.environ[REPO_ROOT_ENV]).resolve()

    # Git is authoritative for root resolution.
    cp = _run_git(["rev-parse", "--show-toplevel"], cwd=Path.cwd())
    return Path(cp.stdout.strip()).resolve()


def _safe_repo_path(repo_root: Path, rel_path: str) -> Optional[Path]:
    """
    Convert a repo-relative path into an absolute path under repo_root.

    Security: reject paths that escape repo_root.
    """
    try:
        abs_path = (repo_root / rel_path).resolve()
        abs_path.relative_to(repo_root.resolve())
        return abs_path
    except Exception:
        return None


def _is_text_file_bytes(buf: bytes) -> bool:
    # Heuristic: NUL bytes => binary-ish.
    return b"\x00" not in buf


def _load_engine(config_path: Optional[Path]):
    # Local imports: keep gate script usable without installing as a package.
    sys.path.insert(0, str((Path(__file__).parent).resolve()))
    from config.agent_config import AgentConfig  # pylint: disable=import-error
    from audit_engine.auditor import AuditorEngine  # pylint: disable=import-error

    try:
        cfg = AgentConfig(str(config_path) if config_path else None)
    except (RuntimeError, FileNotFoundError, ValueError, TypeError) as e:
        # Gate must stay operational even when optional dependencies (e.g., pyyaml) are missing.
        sys.stderr.write(f"[auditor-gate] config load skipped: {e}\n")
        cfg = AgentConfig(None)

    # Gate is deterministic: disable AI in hooks/CI unless explicitly implemented otherwise.
    cfg.enable_ai = False
    engine = AuditorEngine(cfg)
    engine.start()
    return engine


def _staged_paths(repo_root: Path) -> list[str]:
    cp = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=repo_root)
    return [p for p in cp.stdout.splitlines() if p.strip()]


def _read_index_blob(repo_root: Path, path: str) -> str:
    # ":" syntax reads from the index (staging area)
    cp = _run_git(["show", f":{path}"], cwd=repo_root)
    return cp.stdout


def _limit_text(text: str, limit_chars: int) -> str:
    if len(text) <= limit_chars:
        return text
    return text[:limit_chars] + "\n... [truncated] ..."


def _analyze_staged_content(engine, repo_root: Path, max_chars_per_file: int) -> list[Violation]:
    violations: list[Violation] = []

    for p in _staged_paths(repo_root):
        try:
            content = _read_index_blob(repo_root, p)
        except subprocess.CalledProcessError as e:
            # If a file cannot be read from index, skip with explicit rationale.
            # This keeps gating deterministic without blocking on non-text artifacts.
            sys.stderr.write(f"[auditor-gate] SKIP unreadable index blob: {p}\n")
            sys.stderr.write(_limit_text(e.stderr, 1000) + "\n")
            continue

        event = {
            "type": "tool",
            "tool_name": "FileEdit",
            "tool_input": {
                "file_path": p,
                "old_string": "",
                "new_string": _limit_text(content, max_chars_per_file),
            },
        }

        res = engine.analyze_event(event)
        if not res:
            continue

        violations.append(
            Violation(
                rule_name=res.rule_name,
                severity=res.severity,
                action=res.action,
                description=res.description,
                location=res.location or p,
                suggestion=res.suggestion,
            )
        )

    return violations


def _analyze_commit_message(engine, commit_msg_path: Path) -> list[Violation]:
    msg = commit_msg_path.read_text(encoding="utf-8", errors="replace")
    event = {"type": "status", "status_detail": msg}
    res = engine.analyze_event(event)
    if not res:
        return []
    return [
        Violation(
            rule_name=res.rule_name,
            severity=res.severity,
            action=res.action,
            description=res.description,
            location=str(commit_msg_path),
            suggestion=res.suggestion,
        )
    ]


def _parse_pre_push_ranges(stdin: str) -> list[tuple[str, str]]:
    """
    Parse pre-push stdin:
      <local ref> <local sha1> <remote ref> <remote sha1>
    """
    ranges: list[tuple[str, str]] = []
    for line in stdin.splitlines():
        parts = line.strip().split()
        if len(parts) != 4:
            continue
        _local_ref, local_sha, _remote_ref, remote_sha = parts
        ranges.append((remote_sha, local_sha))
    return ranges


def _rev_list(repo_root: Path, rev_range: str) -> list[str]:
    cp = _run_git(["rev-list", rev_range], cwd=repo_root)
    return [s for s in cp.stdout.splitlines() if s.strip()]


def _commit_patch(repo_root: Path, sha: str, max_chars: int) -> str:
    cp = _run_git(["show", "--format=", "--unified=0", sha], cwd=repo_root)
    return _limit_text(cp.stdout, max_chars)


def _analyze_pre_push(engine, repo_root: Path, stdin: str, max_chars_per_commit: int) -> list[Violation]:
    violations: list[Violation] = []
    for remote_sha, local_sha in _parse_pre_push_ranges(stdin):
        if local_sha == "0" * 40:
            continue
        is_bootstrap = remote_sha == "0" * 40
        if is_bootstrap:
            # Incremental adoption: on an empty remote, limit analysis to last N commits.
            max_commits = int(os.environ.get(BOOTSTRAP_MAX_COMMITS_ENV, "50"))
            cp = _run_git(["rev-list", f"--max-count={max_commits}", local_sha], cwd=repo_root)
            shas = [s for s in cp.stdout.splitlines() if s.strip()]
        else:
            rev_range = f"{remote_sha}..{local_sha}"
            shas = _rev_list(repo_root, rev_range)

        for sha in shas:
            patch = _commit_patch(repo_root, sha, max_chars_per_commit)
            event = {
                "type": "tool",
                "tool_name": "FileEdit",
                "tool_input": {
                    "file_path": f"commit:{sha}",
                    "old_string": "",
                    "new_string": patch,
                },
            }
            res = engine.analyze_event(event)
            if not res:
                continue
            violations.append(
                Violation(
                    rule_name=res.rule_name,
                    severity=res.severity,
                    action=res.action,
                    description=res.description,
                    location=f"commit:{sha}",
                    suggestion=res.suggestion,
                )
            )
    return violations


def _render_violations(violations: Iterable[Violation]) -> str:
    out_lines: list[str] = []
    for v in violations:
        out_lines.append(
            f"- rule={v.rule_name} severity={v.severity} action={v.action} location={v.location} desc={v.description}"
        )
        if v.suggestion:
            out_lines.append(f"  suggestion: {v.suggestion}")
    return "\n".join(out_lines)


def _has_blocking(violations: Iterable[Violation]) -> bool:
    return any(v.action == "block" for v in violations)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="auditor-gate")
    ap.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path config YAML (default: config/agent_config.yaml)",
    )
    ap.add_argument(
        "--max-chars-per-file",
        type=int,
        default=200_000,
        help="Max characters per staged file analyzed in pre-commit.",
    )
    ap.add_argument(
        "--max-chars-per-commit",
        type=int,
        default=400_000,
        help="Max characters per commit patch analyzed in pre-push.",
    )

    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pre-commit")

    p_commit_msg = sub.add_parser("commit-msg")
    p_commit_msg.add_argument("commit_msg_file", type=str)

    p_pre_push = sub.add_parser("pre-push")
    p_pre_push.add_argument("--remote-name", type=str, default="")
    p_pre_push.add_argument("--remote-url", type=str, default="")

    p_ci = sub.add_parser("ci")
    p_ci.add_argument("--range", type=str, required=True, help="Git revision range, e.g. A...B or A..B")

    sub.add_parser("install-hooks")

    args = ap.parse_args(argv)

    repo_root = _repo_root()
    default_cfg = repo_root / "config" / "agent_config.yaml"
    config_path = Path(args.config).resolve() if args.config else default_cfg

    if args.cmd == "install-hooks":
        hooks_dir = repo_root / ".githooks"
        if not hooks_dir.exists():
            sys.stderr.write(f"[auditor-gate] hooks directory not found: {hooks_dir}\n")
            return 2
        _run_git(["config", "core.hooksPath", ".githooks"], cwd=repo_root)
        for name in ["pre-commit", "commit-msg", "pre-push"]:
            hp = hooks_dir / name
            if hp.exists():
                hp.chmod(0o755)
        sys.stderr.write("[auditor-gate] hooks installed (core.hooksPath=.githooks)\n")
        return 0

    if not config_path.exists():
        sys.stderr.write(f"[auditor-gate] config not found: {config_path}\n")
        return 2

    engine = _load_engine(config_path)
    try:
        if args.cmd == "pre-commit":
            violations = _analyze_staged_content(engine, repo_root, args.max_chars_per_file)
        elif args.cmd == "commit-msg":
            violations = _analyze_commit_message(engine, Path(args.commit_msg_file))
        elif args.cmd == "pre-push":
            stdin = sys.stdin.read()
            violations = _analyze_pre_push(engine, repo_root, stdin, args.max_chars_per_commit)
        elif args.cmd == "ci":
            cp = _run_git(["diff", "--name-only", args.range], cwd=repo_root)
            paths = [p for p in cp.stdout.splitlines() if p.strip()]
            violations = []
            for p in paths:
                try:
                    abs_p = _safe_repo_path(repo_root, p)
                    if abs_p is None:
                        sys.stderr.write(f"[auditor-gate] SKIP unsafe path: {p}\n")
                        continue
                    buf = abs_p.read_bytes()
                    if not _is_text_file_bytes(buf):
                        sys.stderr.write(f"[auditor-gate] SKIP non-text file: {p}\n")
                        continue
                    content = buf.decode("utf-8", errors="replace")
                except OSError as e:
                    sys.stderr.write(f"[auditor-gate] SKIP unreadable file: {p}\n")
                    sys.stderr.write(_limit_text(str(e), 500) + "\n")
                    continue
                event = {
                    "type": "tool",
                    "tool_name": "FileEdit",
                    "tool_input": {"file_path": p, "old_string": "", "new_string": _limit_text(content, args.max_chars_per_file)},
                }
                res = engine.analyze_event(event)
                if res:
                    violations.append(
                        Violation(
                            rule_name=res.rule_name,
                            severity=res.severity,
                            action=res.action,
                            description=res.description,
                            location=res.location or p,
                            suggestion=res.suggestion,
                        )
                    )
        else:
            sys.stderr.write(f"[auditor-gate] unsupported cmd: {args.cmd}\n")
            return 2

        if not violations:
            return 0

        sys.stderr.write("[auditor-gate] violations detected:\n")
        sys.stderr.write(_render_violations(violations) + "\n")

        if _has_blocking(violations):
            sys.stderr.write("[auditor-gate] decision=DENY (blocking violation)\n")
            return 1

        sys.stderr.write("[auditor-gate] decision=ALLOW (no blocking violation)\n")
        return 0
    finally:
        engine.stop()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


