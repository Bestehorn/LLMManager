"""GitHub API wrapper for CI/CD, issue, and PR operations.

Usage:
    python scripts/github_wrapper.py list-workflows
    python scripts/github_wrapper.py list-runs --limit 5
    python scripts/github_wrapper.py get-logs <run_id> --failed-only
    python scripts/github_wrapper.py list-issues
    python scripts/github_wrapper.py list-issues --state open --assignee "*" --label in-progress
    python scripts/github_wrapper.py create-issue --title "..." --body "..."
    python scripts/github_wrapper.py create-pr --head <branch> --base main --title "..." --body-file <path>
    python scripts/github_wrapper.py get-pr <pr_number>
    python scripts/github_wrapper.py get-pr-checks <pr_number>
    python scripts/github_wrapper.py approve-pr <pr_number>
    python scripts/github_wrapper.py merge-pr <pr_number> --method squash
    python scripts/github_wrapper.py delete-remote-branch <branch>

Credentials: credentials/github-pat.txt (one-line PAT, gitignored).
The owner/repo are auto-detected from .git/config — do NOT hardcode them.

This wrapper is the project's mandated entry point for all GitHub API
operations (see .kiro/steering/use-git-wrapper-scripts.md). Direct use
of `gh`, `glab`, raw curl, or requests against api.github.com is
forbidden.
"""

from __future__ import annotations

import argparse
import configparser
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen

CREDENTIALS_FILE = Path("credentials") / "github-pat.txt"
PLACEHOLDER = "PASTE_YOUR_GITHUB_PAT_HERE"
API_ROOT = "https://api.github.com"

FIELD_MESSAGE = "message"
FIELD_TITLE = "title"
FIELD_BODY = "body"
FIELD_STATE = "state"
FIELD_LABELS = "labels"
FIELD_WORKFLOWS = "workflows"
FIELD_WORKFLOW_RUNS = "workflow_runs"
FIELD_JOBS = "jobs"
FIELD_NAME = "name"
FIELD_CONCLUSION = "conclusion"

logger = logging.getLogger("github_wrapper")


class GitHubAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int = 0, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def _detect_repo() -> tuple[str, str]:
    """Parse .git/config to extract (owner, repo) from origin URL."""
    cfg_path = Path(".git") / "config"
    if not cfg_path.exists():
        raise GitHubAPIError("Not a git repository (no .git/config found).")
    parser = configparser.ConfigParser()
    parser.read(cfg_path)
    url = parser['remote "origin"']["url"]
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)(?:\.git)?/?$", url)
    if not m:
        raise GitHubAPIError(f"Could not parse GitHub owner/repo from origin URL: {url}")
    return m.group(1), m.group(2)


def _load_token() -> str:
    if not CREDENTIALS_FILE.exists():
        raise GitHubAPIError(
            f"Missing credentials file: {CREDENTIALS_FILE}. "
            "Create it from credentials/github-pat.txt.template."
        )
    token = CREDENTIALS_FILE.read_text(encoding="utf-8").strip()
    if not token or token == PLACEHOLDER:
        raise GitHubAPIError(
            f"{CREDENTIALS_FILE} still contains the placeholder. Paste a real PAT."
        )
    return token


def _api_request(
    *,
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> Any:
    url = f"{API_ROOT}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(url=url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        # nosec B310: url is always built from the fixed https API_ROOT, no file:/custom scheme.
        with urlopen(req) as resp:  # nosec B310
            data = resp.read().decode("utf-8")
            return json.loads(data) if data else {}
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise GitHubAPIError(
            f"GitHub API error: {exc.code} {exc.reason}",
            status_code=exc.code,
            details=details,
        ) from exc


def _paginate(*, path: str, token: str, params: dict[str, Any] | None = None) -> list[Any]:
    """Follow GitHub's page-based pagination, returning the concatenated list."""
    results: list[Any] = []
    page = 1
    query = dict(params or {})
    query.setdefault("per_page", 100)
    while True:
        query["page"] = page
        sep = "&" if "?" in path else "?"
        chunk = _api_request(method="GET", path=f"{path}{sep}{urlencode(query)}", token=token)
        if not isinstance(chunk, list):
            return chunk  # endpoint returned a single object, not a list
        results.extend(chunk)
        if len(chunk) < query["per_page"]:
            break
        page += 1
    return results


class _NoAuthRedirectHandler(HTTPRedirectHandler):
    """Strip the Authorization header before following a redirect.

    GitHub's logs endpoint returns a 302 to Azure Blob Storage; forwarding the
    GitHub bearer token to that host both fails and leaks the credential.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None:
            new.headers = {k: v for k, v in new.headers.items() if k.lower() != "authorization"}
        return new


def _print(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# Auth / connectivity
# ---------------------------------------------------------------------------
def cmd_whoami(*, owner: str, repo: str, token: str) -> None:
    """Verify the token authenticates and can see the repo."""
    user = _api_request(method="GET", path="/user", token=token)
    repo_info = _api_request(method="GET", path=f"/repos/{owner}/{repo}", token=token)
    _print(
        {
            "authenticated_as": user.get("login"),
            "user_id": user.get("id"),
            "repo": repo_info.get("full_name"),
            "repo_private": repo_info.get("private"),
            "permissions": repo_info.get("permissions"),
            "default_branch": repo_info.get("default_branch"),
        }
    )


# ---------------------------------------------------------------------------
# Workflows / runs / logs
# ---------------------------------------------------------------------------
def cmd_list_workflows(*, owner: str, repo: str, token: str) -> None:
    data = _api_request(method="GET", path=f"/repos/{owner}/{repo}/actions/workflows", token=token)
    workflows = data.get(FIELD_WORKFLOWS, []) if isinstance(data, dict) else []
    _print(
        [
            {"id": w.get("id"), FIELD_NAME: w.get(FIELD_NAME), FIELD_STATE: w.get(FIELD_STATE)}
            for w in workflows
        ]
    )


def cmd_list_runs(*, owner: str, repo: str, token: str, limit: int, branch: str | None) -> None:
    params: dict[str, Any] = {"per_page": limit}
    if branch:
        params["branch"] = branch
    path = f"/repos/{owner}/{repo}/actions/runs?{urlencode(params)}"
    data = _api_request(method="GET", path=path, token=token)
    runs = data.get(FIELD_WORKFLOW_RUNS, []) if isinstance(data, dict) else []
    _print(
        [
            {
                "id": r.get("id"),
                FIELD_NAME: r.get(FIELD_NAME),
                "head_branch": r.get("head_branch"),
                "head_sha": r.get("head_sha"),
                FIELD_STATE: r.get("status"),
                FIELD_CONCLUSION: r.get(FIELD_CONCLUSION),
                "event": r.get("event"),
                "html_url": r.get("html_url"),
            }
            for r in runs[:limit]
        ]
    )


def cmd_get_run(*, owner: str, repo: str, token: str, run_id: int) -> None:
    r = _api_request(method="GET", path=f"/repos/{owner}/{repo}/actions/runs/{run_id}", token=token)
    _print(
        {
            "id": r.get("id"),
            FIELD_NAME: r.get(FIELD_NAME),
            FIELD_STATE: r.get("status"),
            FIELD_CONCLUSION: r.get(FIELD_CONCLUSION),
            "head_branch": r.get("head_branch"),
            "head_sha": r.get("head_sha"),
            "html_url": r.get("html_url"),
        }
    )


def cmd_get_jobs(*, owner: str, repo: str, token: str, run_id: int) -> None:
    data = _api_request(
        method="GET", path=f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs", token=token
    )
    jobs = data.get(FIELD_JOBS, []) if isinstance(data, dict) else []
    _print(
        [
            {
                "id": j.get("id"),
                FIELD_NAME: j.get(FIELD_NAME),
                FIELD_STATE: j.get("status"),
                FIELD_CONCLUSION: j.get(FIELD_CONCLUSION),
            }
            for j in jobs
        ]
    )


def cmd_get_logs(*, owner: str, repo: str, token: str, run_id: int) -> None:
    """Download a run's logs (zip). Follows the 302 to blob storage without the token."""
    url = f"{API_ROOT}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    req = Request(url=url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    opener = build_opener(_NoAuthRedirectHandler())
    out = Path("tmp") / f"run-{run_id}-logs.zip"
    out.parent.mkdir(exist_ok=True)
    # nosec B310: url built from the fixed https API_ROOT.
    with opener.open(req) as resp:  # nosec B310
        out.write_bytes(resp.read())
    _print({"saved": str(out), "bytes": out.stat().st_size})


def cmd_rerun(*, owner: str, repo: str, token: str, run_id: int) -> None:
    _api_request(
        method="POST", path=f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun", token=token
    )
    _print({"rerun_requested": run_id})


def cmd_cancel(*, owner: str, repo: str, token: str, run_id: int) -> None:
    _api_request(
        method="POST", path=f"/repos/{owner}/{repo}/actions/runs/{run_id}/cancel", token=token
    )
    _print({"cancel_requested": run_id})


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------
def _is_in_progress(issue: dict[str, Any]) -> bool:
    if issue.get("assignees") or issue.get("assignee"):
        return True
    labels = {lbl.get(FIELD_NAME, "").lower() for lbl in issue.get(FIELD_LABELS, [])}
    return bool(labels & {"in-progress", "in progress", "wip", "doing"})


def cmd_list_issues(
    *,
    owner: str,
    repo: str,
    token: str,
    state: str,
    assignee: str | None,
    label: str | None,
) -> None:
    params: dict[str, Any] = {FIELD_STATE: state}
    if assignee:
        params["assignee"] = assignee
    if label:
        params["labels"] = label
    issues = _paginate(path=f"/repos/{owner}/{repo}/issues", token=token, params=params)
    out = []
    for it in issues:
        if "pull_request" in it:
            continue  # the issues endpoint also returns PRs; skip them
        out.append(
            {
                "number": it.get("number"),
                FIELD_TITLE: it.get(FIELD_TITLE),
                FIELD_STATE: it.get(FIELD_STATE),
                "labels": [lbl.get(FIELD_NAME) for lbl in it.get(FIELD_LABELS, [])],
                "assignees": [a.get("login") for a in it.get("assignees", [])],
                "in_progress": _is_in_progress(it),
                "html_url": it.get("html_url"),
            }
        )
    _print(out)


def cmd_get_issue(*, owner: str, repo: str, token: str, number: int) -> None:
    it = _api_request(method="GET", path=f"/repos/{owner}/{repo}/issues/{number}", token=token)
    _print(
        {
            "number": it.get("number"),
            FIELD_TITLE: it.get(FIELD_TITLE),
            FIELD_STATE: it.get(FIELD_STATE),
            FIELD_BODY: it.get(FIELD_BODY),
            "labels": [lbl.get(FIELD_NAME) for lbl in it.get(FIELD_LABELS, [])],
            "assignees": [a.get("login") for a in it.get("assignees", [])],
            "in_progress": _is_in_progress(it),
            "html_url": it.get("html_url"),
        }
    )


def cmd_get_issue_comments(*, owner: str, repo: str, token: str, number: int) -> None:
    comments = _paginate(path=f"/repos/{owner}/{repo}/issues/{number}/comments", token=token)
    _print(
        [{"user": c.get("user", {}).get("login"), FIELD_BODY: c.get(FIELD_BODY)} for c in comments]
    )


def cmd_comment_issue(*, owner: str, repo: str, token: str, number: int, body: str) -> None:
    c = _api_request(
        method="POST",
        path=f"/repos/{owner}/{repo}/issues/{number}/comments",
        token=token,
        payload={FIELD_BODY: body},
    )
    _print({"comment_id": c.get("id"), "html_url": c.get("html_url")})


def cmd_update_issue(
    *,
    owner: str,
    repo: str,
    token: str,
    number: int,
    state: str | None,
    add_labels: list[str] | None,
) -> None:
    payload: dict[str, Any] = {}
    if state:
        payload[FIELD_STATE] = state
    if add_labels:
        existing = _api_request(
            method="GET", path=f"/repos/{owner}/{repo}/issues/{number}", token=token
        )
        current = [lbl.get(FIELD_NAME) for lbl in existing.get(FIELD_LABELS, [])]
        payload[FIELD_LABELS] = sorted(set(current) | set(add_labels))
    it = _api_request(
        method="PATCH",
        path=f"/repos/{owner}/{repo}/issues/{number}",
        token=token,
        payload=payload,
    )
    _print({"number": it.get("number"), FIELD_STATE: it.get(FIELD_STATE)})


def cmd_create_issue(
    *,
    owner: str,
    repo: str,
    token: str,
    title: str,
    body: str,
    labels: list[str] | None,
) -> None:
    payload: dict[str, Any] = {FIELD_TITLE: title, FIELD_BODY: body}
    if labels:
        payload[FIELD_LABELS] = labels
    it = _api_request(
        method="POST", path=f"/repos/{owner}/{repo}/issues", token=token, payload=payload
    )
    _print(
        {
            "number": it.get("number"),
            FIELD_TITLE: it.get(FIELD_TITLE),
            "html_url": it.get("html_url"),
        }
    )


# ---------------------------------------------------------------------------
# Pull requests / merge / CI lifecycle
# ---------------------------------------------------------------------------
def cmd_create_pr(
    *,
    owner: str,
    repo: str,
    token: str,
    head: str,
    base: str,
    title: str,
    body: str,
) -> None:
    pr = _api_request(
        method="POST",
        path=f"/repos/{owner}/{repo}/pulls",
        token=token,
        payload={FIELD_TITLE: title, FIELD_BODY: body, "head": head, "base": base},
    )
    _print(
        {
            "number": pr.get("number"),
            "html_url": pr.get("html_url"),
            FIELD_STATE: pr.get(FIELD_STATE),
        }
    )


def cmd_get_pr(*, owner: str, repo: str, token: str, number: int) -> None:
    pr = _api_request(method="GET", path=f"/repos/{owner}/{repo}/pulls/{number}", token=token)
    reviews = _api_request(
        method="GET", path=f"/repos/{owner}/{repo}/pulls/{number}/reviews", token=token
    )
    review_states = [r.get(FIELD_STATE) for r in reviews] if isinstance(reviews, list) else []
    _print(
        {
            "number": pr.get("number"),
            FIELD_STATE: pr.get(FIELD_STATE),
            "merged": pr.get("merged"),
            "draft": pr.get("draft"),
            "mergeable": pr.get("mergeable"),
            "mergeable_state": pr.get("mergeable_state"),
            "head": pr.get("head", {}).get("ref"),
            "head_sha": pr.get("head", {}).get("sha"),
            "base": pr.get("base", {}).get("ref"),
            "review_states": review_states,
            "html_url": pr.get("html_url"),
        }
    )


def cmd_get_pr_checks(*, owner: str, repo: str, token: str, number: int) -> None:
    pr = _api_request(method="GET", path=f"/repos/{owner}/{repo}/pulls/{number}", token=token)
    sha = pr.get("head", {}).get("sha")
    check_runs = _api_request(
        method="GET", path=f"/repos/{owner}/{repo}/commits/{sha}/check-runs", token=token
    )
    status = _api_request(
        method="GET", path=f"/repos/{owner}/{repo}/commits/{sha}/status", token=token
    )
    runs = check_runs.get("check_runs", []) if isinstance(check_runs, dict) else []
    _print(
        {
            "head_sha": sha,
            "combined_state": status.get(FIELD_STATE) if isinstance(status, dict) else None,
            "check_runs": [
                {
                    FIELD_NAME: c.get(FIELD_NAME),
                    FIELD_STATE: c.get("status"),
                    FIELD_CONCLUSION: c.get(FIELD_CONCLUSION),
                }
                for c in runs
            ],
        }
    )


def cmd_approve_pr(*, owner: str, repo: str, token: str, number: int) -> None:
    try:
        _api_request(
            method="POST",
            path=f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            token=token,
            payload={"event": "APPROVE"},
        )
        _print({"approved": number})
    except GitHubAPIError as exc:
        if exc.status_code == 422:
            _print(
                {
                    "approved": False,
                    "reason": "Cannot approve your own PR (HTTP 422). "
                    "An external approval is required before merge.",
                }
            )
        else:
            raise


def cmd_merge_pr(*, owner: str, repo: str, token: str, number: int, method: str) -> None:
    res = _api_request(
        method="PUT",
        path=f"/repos/{owner}/{repo}/pulls/{number}/merge",
        token=token,
        payload={"merge_method": method},
    )
    _print(
        {"merged": res.get("merged"), FIELD_MESSAGE: res.get(FIELD_MESSAGE), "sha": res.get("sha")}
    )


def cmd_delete_remote_branch(*, owner: str, repo: str, token: str, branch: str) -> None:
    _api_request(
        method="DELETE", path=f"/repos/{owner}/{repo}/git/refs/heads/{branch}", token=token
    )
    _print({"deleted_branch": branch})


def _add_int(sub: argparse.ArgumentParser, name: str) -> None:
    sub.add_argument(name, type=int)


def main() -> None:
    parser = argparse.ArgumentParser(description="GitHub API wrapper for Bestehorn/LLMManager")
    sub = parser.add_subparsers(dest="subcommand", required=True)

    sub.add_parser("whoami", help="Verify auth and repo visibility")
    sub.add_parser("list-workflows")

    p = sub.add_parser("list-runs")
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--branch", default=None)

    for name in ("get-run", "get-jobs", "get-logs", "rerun", "cancel"):
        p = sub.add_parser(name)
        _add_int(p, "run_id")

    p = sub.add_parser("list-issues")
    p.add_argument("--state", default="open", choices=["open", "closed", "all"])
    p.add_argument("--assignee", default=None)
    p.add_argument("--label", default=None)

    for name in ("get-issue", "get-issue-comments"):
        p = sub.add_parser(name)
        _add_int(p, "number")

    p = sub.add_parser("comment-issue")
    _add_int(p, "number")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--body")
    g.add_argument("--body-file")

    p = sub.add_parser("update-issue")
    _add_int(p, "number")
    p.add_argument("--state", choices=["open", "closed"], default=None)
    p.add_argument("--add-label", action="append", dest="add_labels", default=None)

    p = sub.add_parser("create-issue")
    p.add_argument("--title", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--body")
    g.add_argument("--body-file")
    p.add_argument("--label", action="append", dest="labels", default=None)

    p = sub.add_parser("create-pr")
    p.add_argument("--head", required=True)
    p.add_argument("--base", default="main")
    p.add_argument("--title", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--body")
    g.add_argument("--body-file")

    for name in ("get-pr", "get-pr-checks", "approve-pr"):
        p = sub.add_parser(name)
        _add_int(p, "number")

    p = sub.add_parser("merge-pr")
    _add_int(p, "number")
    p.add_argument("--method", choices=["merge", "squash", "rebase"], default="squash")

    p = sub.add_parser("delete-remote-branch")
    p.add_argument("branch")

    args = parser.parse_args()
    owner, repo = _detect_repo()
    token = _load_token()

    def _body(a: argparse.Namespace) -> str:
        if getattr(a, "body_file", None):
            return Path(a.body_file).read_text(encoding="utf-8")
        return a.body

    cmd = args.subcommand
    if cmd == "whoami":
        cmd_whoami(owner=owner, repo=repo, token=token)
    elif cmd == "list-workflows":
        cmd_list_workflows(owner=owner, repo=repo, token=token)
    elif cmd == "list-runs":
        cmd_list_runs(owner=owner, repo=repo, token=token, limit=args.limit, branch=args.branch)
    elif cmd == "get-run":
        cmd_get_run(owner=owner, repo=repo, token=token, run_id=args.run_id)
    elif cmd == "get-jobs":
        cmd_get_jobs(owner=owner, repo=repo, token=token, run_id=args.run_id)
    elif cmd == "get-logs":
        cmd_get_logs(owner=owner, repo=repo, token=token, run_id=args.run_id)
    elif cmd == "rerun":
        cmd_rerun(owner=owner, repo=repo, token=token, run_id=args.run_id)
    elif cmd == "cancel":
        cmd_cancel(owner=owner, repo=repo, token=token, run_id=args.run_id)
    elif cmd == "list-issues":
        cmd_list_issues(
            owner=owner,
            repo=repo,
            token=token,
            state=args.state,
            assignee=args.assignee,
            label=args.label,
        )
    elif cmd == "get-issue":
        cmd_get_issue(owner=owner, repo=repo, token=token, number=args.number)
    elif cmd == "get-issue-comments":
        cmd_get_issue_comments(owner=owner, repo=repo, token=token, number=args.number)
    elif cmd == "comment-issue":
        cmd_comment_issue(owner=owner, repo=repo, token=token, number=args.number, body=_body(args))
    elif cmd == "update-issue":
        cmd_update_issue(
            owner=owner,
            repo=repo,
            token=token,
            number=args.number,
            state=args.state,
            add_labels=args.add_labels,
        )
    elif cmd == "create-issue":
        cmd_create_issue(
            owner=owner,
            repo=repo,
            token=token,
            title=args.title,
            body=_body(args),
            labels=args.labels,
        )
    elif cmd == "create-pr":
        cmd_create_pr(
            owner=owner,
            repo=repo,
            token=token,
            head=args.head,
            base=args.base,
            title=args.title,
            body=_body(args),
        )
    elif cmd == "get-pr":
        cmd_get_pr(owner=owner, repo=repo, token=token, number=args.number)
    elif cmd == "get-pr-checks":
        cmd_get_pr_checks(owner=owner, repo=repo, token=token, number=args.number)
    elif cmd == "approve-pr":
        cmd_approve_pr(owner=owner, repo=repo, token=token, number=args.number)
    elif cmd == "merge-pr":
        cmd_merge_pr(owner=owner, repo=repo, token=token, number=args.number, method=args.method)
    elif cmd == "delete-remote-branch":
        cmd_delete_remote_branch(owner=owner, repo=repo, token=token, branch=args.branch)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        main()
    except GitHubAPIError as exc:
        logger.error("%s", exc)
        if exc.details:
            logger.error("%s", exc.details)
        sys.exit(1)
