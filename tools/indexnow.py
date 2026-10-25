#!/usr/bin/env python3
"""Map this repo's changed files to sitemap URLs and optionally ping IndexNow.

Only URLs that already appear as <loc> in a local sitemap urlset are eligible.
Remote sitemapindex children (/image-converter/, /pdf/) are not fetched or pinged.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HOST = "noclaudkit.com"
ORIGIN = f"https://{HOST}"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
GITHUB_API = "https://api.github.com"
WORKFLOW_FILE = "indexnow.yml"
WORKFLOW_BRANCH = "main"
URL_LIST_CAP = 10_000
KEY_NAME_RE = re.compile(r"^[0-9a-f]{8,128}\.txt$")

# Site-wide chrome / generator that affect every home-page language variant.
SHARED_SITE_FILES = frozenset(
    {
        "home.css",
        "theme.js",
        "favicon.svg",
        "tools/genhome.py",
    }
)


class IndexNowError(Exception):
    """User-facing script failure."""


def normalize_repo_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_canonical_url(url: str, host: str = HOST) -> bool:
    if not url:
        return False
    prefix = f"https://{host}/"
    if url != prefix and not url.startswith(prefix):
        return False
    if any(ch in url for ch in "#?"):
        return False
    return True


def parse_local_urlsets(repo_root: Path) -> tuple[set[str], dict[str, set[str]]]:
    """Return (locs, alternates) from local urlset sitemaps only.

    sitemapindex files are ignored so /image-converter/ and /pdf/ are not pulled in.
    """
    locs: set[str] = set()
    alternates: dict[str, set[str]] = {}
    for path in sorted(repo_root.glob("sitemap*.xml")):
        try:
            tree = ET.parse(path)
        except ET.ParseError:
            continue
        root = tree.getroot()
        tag = root.tag.rsplit("}", 1)[-1]
        if tag != "urlset":
            continue
        for url_el in root.findall(".//{*}url"):
            loc_el = url_el.find("{*}loc")
            if loc_el is None or not loc_el.text:
                continue
            loc = loc_el.text.strip()
            if not is_canonical_url(loc):
                continue
            locs.add(loc)
            alts = alternates.setdefault(loc, set())
            for link in url_el.findall("{*}link"):
                if link.get("rel") != "alternate":
                    continue
                href = (link.get("href") or "").strip()
                if is_canonical_url(href):
                    alts.add(href)
    return locs, alternates


def candidate_urls_for_file(relpath: str) -> set[str] | None:
    """Map a repo file to candidate page URLs, or None to mean every sitemap loc."""
    relpath = normalize_repo_path(relpath)
    if not relpath or relpath.startswith(".git/"):
        return set()
    if relpath in SHARED_SITE_FILES:
        return None
    if not relpath.endswith(".html"):
        return set()
    if relpath.endswith("index.html"):
        directory = relpath[: -len("index.html")]
        return {f"{ORIGIN}/{directory}"}
    stem = relpath[: -len(".html")]
    return {
        f"{ORIGIN}/{relpath}",
        f"{ORIGIN}/{stem}",
        f"{ORIGIN}/{stem}/",
    }


def map_changed_files(
    changed_files: list[str],
    sitemap_locs: set[str],
    alternates: dict[str, set[str]],
) -> list[str]:
    urls: set[str] = set()
    for raw in changed_files:
        candidates = candidate_urls_for_file(raw)
        if candidates is None:
            matched = set(sitemap_locs)
        else:
            matched = {url for url in candidates if url in sitemap_locs}
        for url in matched:
            urls.add(url)
            for alt in alternates.get(url, ()):
                if alt in sitemap_locs:
                    urls.add(alt)
    return sorted(urls)[:URL_LIST_CAP]


def changed_files_between(repo_root: Path, before: str, after: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMR", before, after],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
        raise IndexNowError(f"git diff failed: {detail}")
    return [normalize_repo_path(line) for line in result.stdout.splitlines() if line.strip()]


def first_parent(repo_root: Path, sha: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{sha}^1"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip() or f"exit {result.returncode}"
        raise IndexNowError(f"cannot resolve first parent of {sha}: {detail}")
    return result.stdout.strip()


def is_ancestor(repo_root: Path, ancestor: str, sha: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, sha],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def resolve_before(repo_root: Path, after: str, previous_head: str | None) -> str:
    """Prefer the last successful ping SHA when it is an ancestor of `after`."""
    if previous_head and is_ancestor(repo_root, previous_head, after):
        return previous_head
    return first_parent(repo_root, after)


def github_get_json(url: str, token: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def previous_successful_workflow_head(
    repo: str,
    token: str,
    workflow_file: str = WORKFLOW_FILE,
    branch: str = WORKFLOW_BRANCH,
    exclude_run_id: str | None = None,
) -> str | None:
    """Return head_sha of the last successful IndexNow workflow run on main."""
    url = (
        f"{GITHUB_API}/repos/{repo}/actions/workflows/{workflow_file}/runs"
        f"?branch={branch}&status=success&event=workflow_run&per_page=20"
    )
    try:
        data = github_get_json(url, token)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    exclude = str(exclude_run_id) if exclude_run_id else None
    for run in data.get("workflow_runs") or []:
        if exclude and str(run.get("id")) == exclude:
            continue
        if run.get("event") != "workflow_run":
            continue
        if run.get("conclusion") != "success":
            continue
        head = run.get("head_sha")
        if head:
            return str(head)
    return None


def lookup_previous_successful_head() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or ""
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if not token or not repo:
        return None
    return previous_successful_workflow_head(
        repo,
        token,
        exclude_run_id=os.environ.get("GITHUB_RUN_ID") or None,
    )


def resolve_before_sha(repo_root: Path, after: str, before_override: str | None) -> str:
    if before_override:
        return before_override
    return resolve_before(repo_root, after, lookup_previous_successful_head())


def read_key(repo_root: Path) -> tuple[str, str]:
    """Return (key, keyLocation) from the public root key file only."""
    matches: list[Path] = []
    for path in sorted(repo_root.glob("*.txt")):
        if not KEY_NAME_RE.match(path.name):
            continue
        stem = path.stem
        body = path.read_text(encoding="utf-8").strip()
        if body == stem:
            matches.append(path)
    if not matches:
        raise IndexNowError("IndexNow key file not found at repository root")
    if len(matches) > 1:
        raise IndexNowError("multiple IndexNow key files at repository root")
    key_path = matches[0]
    return key_path.stem, f"{ORIGIN}/{key_path.name}"


def build_payload(host: str, key: str, key_location: str, url_list: list[str]) -> dict:
    return {
        "host": host,
        "key": key,
        "keyLocation": key_location,
        "urlList": url_list,
    }


def submit(payload: dict) -> int | str:
    request = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except (urllib.error.URLError, TimeoutError):
        return "error"


def log_status(status: int | str | None, url_count: int) -> None:
    if status is None:
        print(f"status=skipped url_count={url_count}", file=sys.stderr)
    else:
        print(f"status={status} url_count={url_count}", file=sys.stderr)


def collect_urls(repo_root: Path, files: list[str] | None, before: str | None, after: str | None) -> list[str]:
    sitemap_locs, alternates = parse_local_urlsets(repo_root)
    if files is not None:
        changed = [normalize_repo_path(path) for path in files]
    else:
        if not after:
            raise IndexNowError("either --files or --after is required")
        resolved_before = resolve_before_sha(repo_root, after, before)
        changed = changed_files_between(repo_root, resolved_before, after)
    return map_changed_files(changed, sitemap_locs, alternates)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="print the JSON payload and do not send (default if --submit is omitted)",
    )
    mode.add_argument(
        "--submit",
        action="store_true",
        help="POST once to IndexNow; logs HTTP status and URL count only",
    )
    parser.add_argument("--before", help="git SHA for the start of the pushed range")
    parser.add_argument(
        "--after",
        default=os.environ.get("INDEXNOW_AFTER") or None,
        help="git SHA for the end of the pushed range (or INDEXNOW_AFTER)",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        help="explicit changed paths (skips git); useful for tests",
    )
    parser.add_argument("--repo-root", default=".", help="repository root")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dry_run = not args.submit
    repo_root = Path(args.repo_root).resolve()
    try:
        url_list = collect_urls(repo_root, args.files, args.before, args.after)
        key, key_location = read_key(repo_root)
    except IndexNowError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    payload = build_payload(HOST, key, key_location, url_list)
    if dry_run:
        json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0
    if not url_list:
        log_status(None, 0)
        return 0
    status = submit(payload)
    log_status(status, len(url_list))
    return 0 if isinstance(status, int) and 200 <= status < 300 else 1


if __name__ == "__main__":
    sys.exit(main())
