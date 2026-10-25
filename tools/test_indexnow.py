#!/usr/bin/env python3
"""Unit tests for tools/indexnow.py. Run: python3 tools/test_indexnow.py"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import indexnow  # noqa: E402

HOST = "noclaudkit.com"
HOME = f"https://{HOST}/"
HOME_RU = f"https://{HOST}/ru/"
HOME_ZH = f"https://{HOST}/zh/"
HOME_URLS = [HOME, HOME_RU, HOME_ZH]

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">
<url><loc>https://noclaudkit.com/</loc><xhtml:link rel="alternate" hreflang="en" href="https://noclaudkit.com/"/><xhtml:link rel="alternate" hreflang="ru" href="https://noclaudkit.com/ru/"/><xhtml:link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/zh/"/><xhtml:link rel="alternate" hreflang="x-default" href="https://noclaudkit.com/"/></url>
<url><loc>https://noclaudkit.com/ru/</loc><xhtml:link rel="alternate" hreflang="en" href="https://noclaudkit.com/"/><xhtml:link rel="alternate" hreflang="ru" href="https://noclaudkit.com/ru/"/><xhtml:link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/zh/"/></url>
<url><loc>https://noclaudkit.com/zh/</loc><xhtml:link rel="alternate" hreflang="en" href="https://noclaudkit.com/"/><xhtml:link rel="alternate" hreflang="ru" href="https://noclaudkit.com/ru/"/><xhtml:link rel="alternate" hreflang="zh-Hans" href="https://noclaudkit.com/zh/"/></url>
</urlset>
"""

SITEMAP_INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://noclaudkit.com/sitemap-home.xml</loc></sitemap>
<sitemap><loc>https://noclaudkit.com/image-converter/sitemap.xml</loc></sitemap>
<sitemap><loc>https://noclaudkit.com/pdf/sitemap.xml</loc></sitemap>
</sitemapindex>
"""

DIRTY_URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>http://noclaudkit.com/</loc></url>
<url><loc>https://example.com/phish</loc></url>
<url><loc>https://noclaudkit.com/ok/</loc></url>
<url><loc>https://noclaudkit.com/q?x=1</loc></url>
<url><loc>https://www.noclaudkit.com/</loc></url>
</urlset>
"""

FAKE_KEY = "aaaabbbbccccddddeeeeffff00001111"


def write_repo(tmp: Path, urlset: str = URLSET, key: str | None = FAKE_KEY) -> Path:
    tmp.joinpath("sitemap-home.xml").write_text(urlset, encoding="utf-8")
    tmp.joinpath("sitemap.xml").write_text(SITEMAP_INDEX, encoding="utf-8")
    if key is not None:
        tmp.joinpath(f"{key}.txt").write_text(key + "\n", encoding="utf-8")
    return tmp


def mapped(tmp: Path, files: list[str]) -> list[str]:
    locs, alts = indexnow.parse_local_urlsets(tmp)
    return indexnow.map_changed_files(files, locs, alts)


class CanonicalUrlTests(unittest.TestCase):
    def test_accepts_https_host_paths(self):
        self.assertTrue(indexnow.is_canonical_url(HOME))
        self.assertTrue(indexnow.is_canonical_url(HOME_RU))

    def test_rejects_http_other_host_and_query(self):
        self.assertFalse(indexnow.is_canonical_url("http://noclaudkit.com/"))
        self.assertFalse(indexnow.is_canonical_url("https://example.com/"))
        self.assertFalse(indexnow.is_canonical_url("https://www.noclaudkit.com/"))
        self.assertFalse(indexnow.is_canonical_url("https://noclaudkit.com/x?y=1"))
        self.assertFalse(indexnow.is_canonical_url("https://noclaudkit.com/#frag"))


class SitemapParseTests(unittest.TestCase):
    def test_reads_local_urlset_and_alternates(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            locs, alts = indexnow.parse_local_urlsets(tmp)
            self.assertEqual(locs, set(HOME_URLS))
            self.assertEqual(alts[HOME], set(HOME_URLS))

    def test_ignores_sitemapindex_remote_children(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            locs, _ = indexnow.parse_local_urlsets(tmp)
            self.assertNotIn("https://noclaudkit.com/image-converter/sitemap.xml", locs)
            self.assertNotIn("https://noclaudkit.com/pdf/sitemap.xml", locs)
            self.assertTrue(all("/image-converter/" not in url for url in locs))
            self.assertTrue(all("/pdf/" not in url for url in locs))

    def test_drops_non_canonical_locs(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw), urlset=DIRTY_URLSET)
            locs, _ = indexnow.parse_local_urlsets(tmp)
            self.assertEqual(locs, {"https://noclaudkit.com/ok/"})


class MappingTests(unittest.TestCase):
    def test_home_html_expands_to_all_languages(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            self.assertEqual(mapped(tmp, ["index.html"]), HOME_URLS)
            self.assertEqual(mapped(tmp, ["ru/index.html"]), HOME_URLS)
            self.assertEqual(mapped(tmp, ["zh/index.html"]), HOME_URLS)

    def test_shared_assets_map_to_all_sitemap_urls(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            for path in ("home.css", "theme.js", "favicon.svg", "tools/genhome.py"):
                self.assertEqual(mapped(tmp, [path]), HOME_URLS, path)

    def test_other_repo_and_non_page_files_are_ignored(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            ignored = [
                "local-image-converter/index.html",
                "local-image-converter/ru/heic-to-jpg.html",
                "404.html",
                "robots.txt",
                "llms.txt",
                "CNAME",
                "sitemap.xml",
                "sitemap-home.xml",
                f"{FAKE_KEY}.txt",
                ".github/workflows/indexnow.yml",
                "tools/indexnow.py",
            ]
            self.assertEqual(mapped(tmp, ignored), [])

    def test_does_not_emit_image_converter_or_pdf_urls(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            urls = mapped(tmp, ["index.html", "local-image-converter/index.html", "home.css"])
            self.assertEqual(urls, HOME_URLS)
            self.assertFalse(any("image-converter" in url or "/pdf/" in url for url in urls))

    def test_dedupes_and_caps_url_list(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            locs = [f"https://noclaudkit.com/p/{i}/" for i in range(indexnow.URL_LIST_CAP + 25)]
            body = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            ]
            body.extend(f"<url><loc>{loc}</loc></url>" for loc in locs)
            body.append("</urlset>")
            tmp.joinpath("sitemap-home.xml").write_text("\n".join(body), encoding="utf-8")
            files = [f"p/{i}/index.html" for i in range(indexnow.URL_LIST_CAP + 25)]
            urls = mapped(tmp, files)
            self.assertEqual(len(urls), indexnow.URL_LIST_CAP)
            self.assertEqual(urls, sorted(locs)[: indexnow.URL_LIST_CAP])

    def test_empty_change_list(self):
        with tempfile.TemporaryDirectory() as raw:
            self.assertEqual(mapped(write_repo(Path(raw)), []), [])


class KeyAndPayloadTests(unittest.TestCase):
    def test_reads_key_from_root_file(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            key, location = indexnow.read_key(tmp)
            self.assertEqual(key, FAKE_KEY)
            self.assertEqual(location, f"https://noclaudkit.com/{FAKE_KEY}.txt")

    def test_rejects_missing_or_mismatched_key(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw), key=None)
            with self.assertRaises(indexnow.IndexNowError):
                indexnow.read_key(tmp)
            tmp.joinpath("not-a-key.txt").write_text("nope\n", encoding="utf-8")
            with self.assertRaises(indexnow.IndexNowError):
                indexnow.read_key(tmp)
            tmp.joinpath(f"{FAKE_KEY}.txt").write_text("mismatch\n", encoding="utf-8")
            with self.assertRaises(indexnow.IndexNowError):
                indexnow.read_key(tmp)

    def test_payload_shape(self):
        payload = indexnow.build_payload(HOST, FAKE_KEY, f"{HOME}{FAKE_KEY}.txt", HOME_URLS)
        self.assertEqual(
            payload,
            {
                "host": HOST,
                "key": FAKE_KEY,
                "keyLocation": f"{HOME}{FAKE_KEY}.txt",
                "urlList": HOME_URLS,
            },
        )


class CliTests(unittest.TestCase):
    def test_dry_run_prints_payload_and_does_not_post(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            stdout = io.StringIO()
            with mock.patch.object(indexnow.urllib.request, "urlopen") as urlopen:
                with mock.patch.object(sys, "stdout", stdout):
                    code = indexnow.main(
                        ["--dry-run", "--repo-root", str(tmp), "--files", "index.html"]
                    )
            self.assertEqual(code, 0)
            urlopen.assert_not_called()
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["urlList"], HOME_URLS)
            self.assertEqual(payload["host"], HOST)
            self.assertEqual(payload["key"], FAKE_KEY)

    def test_submit_skips_post_when_no_urls(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            stderr = io.StringIO()
            with mock.patch.object(indexnow.urllib.request, "urlopen") as urlopen:
                with mock.patch.object(sys, "stderr", stderr):
                    code = indexnow.main(
                        ["--submit", "--repo-root", str(tmp), "--files", "404.html"]
                    )
            self.assertEqual(code, 0)
            urlopen.assert_not_called()
            self.assertEqual(stderr.getvalue().strip(), "status=skipped url_count=0")

    def test_submit_posts_once_and_logs_status_and_count_only(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            stderr = io.StringIO()
            stdout = io.StringIO()

            class Resp:
                status = 200

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return b""

            with mock.patch.object(indexnow.urllib.request, "urlopen", return_value=Resp()) as urlopen:
                with mock.patch.object(sys, "stderr", stderr), mock.patch.object(sys, "stdout", stdout):
                    code = indexnow.main(
                        ["--submit", "--repo-root", str(tmp), "--files", "ru/index.html", "home.css"]
                    )
            self.assertEqual(code, 0)
            self.assertEqual(urlopen.call_count, 1)
            request = urlopen.call_args[0][0]
            self.assertEqual(request.full_url, indexnow.INDEXNOW_ENDPOINT)
            self.assertEqual(request.get_method(), "POST")
            sent = json.loads(request.data.decode("utf-8"))
            self.assertEqual(sent["urlList"], HOME_URLS)
            self.assertEqual(stderr.getvalue().strip(), "status=200 url_count=3")
            self.assertEqual(stdout.getvalue(), "")

    def test_submit_treats_http_error_as_status(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            stderr = io.StringIO()
            err = urllib.error.HTTPError(
                indexnow.INDEXNOW_ENDPOINT, 403, "Forbidden", hdrs=None, fp=None
            )
            with mock.patch.object(indexnow.urllib.request, "urlopen", side_effect=err):
                with mock.patch.object(sys, "stderr", stderr):
                    code = indexnow.main(
                        ["--submit", "--repo-root", str(tmp), "--files", "index.html"]
                    )
            self.assertEqual(code, 1)
            self.assertEqual(stderr.getvalue().strip(), "status=403 url_count=3")

    def test_submit_urlerror_logs_status_only_and_does_not_leak_key(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = write_repo(Path(raw))
            stderr = io.StringIO()
            stdout = io.StringIO()
            leak = urllib.error.URLError(f"connection failed key={FAKE_KEY} body=secret")
            with mock.patch.object(indexnow.urllib.request, "urlopen", side_effect=leak):
                with mock.patch.object(sys, "stderr", stderr), mock.patch.object(sys, "stdout", stdout):
                    code = indexnow.main(
                        ["--submit", "--repo-root", str(tmp), "--files", "index.html"]
                    )
            self.assertEqual(code, 1)
            logged = stderr.getvalue()
            printed = stdout.getvalue()
            self.assertEqual(logged.strip(), "status=error url_count=3")
            self.assertNotIn(FAKE_KEY, logged)
            self.assertNotIn(FAKE_KEY, printed)
            self.assertNotIn("connection failed", logged)
            self.assertNotIn("secret", logged)


INDEPENDENT_URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://noclaudkit.com/a/</loc></url>
<url><loc>https://noclaudkit.com/b/</loc></url>
</urlset>
"""


def run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def make_multicommit_repo(tmp: Path) -> dict[str, str]:
    """Three commits: base, then /a/, then /b/. Independent sitemap locs."""
    write_repo(tmp, urlset=INDEPENDENT_URLSET)
    run_git(tmp, "init", "-b", "main")
    run_git(tmp, "config", "user.name", "Test")
    run_git(tmp, "config", "user.email", "test@example.com")
    run_git(tmp, "add", ".")
    run_git(tmp, "commit", "-m", "base")
    c1 = run_git(tmp, "rev-parse", "HEAD")
    tmp.joinpath("a").mkdir()
    tmp.joinpath("a", "index.html").write_text("a\n", encoding="utf-8")
    run_git(tmp, "add", "a/index.html")
    run_git(tmp, "commit", "-m", "add a")
    c2 = run_git(tmp, "rev-parse", "HEAD")
    tmp.joinpath("b").mkdir()
    tmp.joinpath("b", "index.html").write_text("b\n", encoding="utf-8")
    run_git(tmp, "add", "b/index.html")
    run_git(tmp, "commit", "-m", "add b")
    c3 = run_git(tmp, "rev-parse", "HEAD")
    return {"c1": c1, "c2": c2, "c3": c3}


class RangeResolutionTests(unittest.TestCase):
    def test_multi_commit_range_includes_earlier_push_commits(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            only_tip = indexnow.changed_files_between(tmp, f"{shas['c3']}^1", shas["c3"])
            since_last_ping = indexnow.changed_files_between(tmp, shas["c1"], shas["c3"])
            self.assertEqual(only_tip, ["b/index.html"])
            self.assertEqual(since_last_ping, ["a/index.html", "b/index.html"])
            self.assertEqual(
                indexnow.collect_urls(tmp, None, shas["c1"], shas["c3"]),
                ["https://noclaudkit.com/a/", "https://noclaudkit.com/b/"],
            )
            with mock.patch.object(indexnow, "lookup_previous_successful_head", return_value=None):
                self.assertEqual(
                    indexnow.collect_urls(tmp, None, None, shas["c3"]),
                    ["https://noclaudkit.com/b/"],
                )

    def test_resolve_before_uses_previous_head_when_ancestor(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            self.assertEqual(
                indexnow.resolve_before(tmp, shas["c3"], shas["c1"]),
                shas["c1"],
            )
            self.assertTrue(indexnow.is_ancestor(tmp, shas["c1"], shas["c3"]))

    def test_resolve_before_falls_back_when_none(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            self.assertEqual(indexnow.resolve_before(tmp, shas["c3"], None), shas["c2"])
            self.assertEqual(indexnow.first_parent(tmp, shas["c3"]), shas["c2"])

    def test_resolve_before_falls_back_when_not_ancestor(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            run_git(tmp, "checkout", "--orphan", "other")
            tmp.joinpath("orphan.txt").write_text("x\n", encoding="utf-8")
            run_git(tmp, "add", "orphan.txt")
            run_git(tmp, "commit", "-m", "orphan")
            orphan = run_git(tmp, "rev-parse", "HEAD")
            run_git(tmp, "checkout", "main")
            self.assertFalse(indexnow.is_ancestor(tmp, orphan, shas["c3"]))
            self.assertEqual(indexnow.resolve_before(tmp, shas["c3"], orphan), shas["c2"])
            self.assertEqual(
                indexnow.resolve_before(tmp, shas["c3"], "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"),
                shas["c2"],
            )

    def test_lookup_skips_current_run_and_returns_previous_head(self):
        payload = {
            "workflow_runs": [
                {
                    "id": 99,
                    "event": "workflow_run",
                    "conclusion": "success",
                    "head_sha": "aaa111",
                },
                {
                    "id": 88,
                    "event": "workflow_run",
                    "conclusion": "success",
                    "head_sha": "bbb222",
                },
            ]
        }
        with mock.patch.object(indexnow, "github_get_json", return_value=payload) as get_json:
            head = indexnow.previous_successful_workflow_head(
                "o/r", "token", exclude_run_id="99"
            )
        self.assertEqual(head, "bbb222")
        url = get_json.call_args[0][0]
        self.assertIn("/repos/o/r/actions/workflows/indexnow.yml/runs", url)
        self.assertIn("branch=main", url)
        self.assertIn("status=success", url)
        self.assertIn("event=workflow_run", url)

    def test_lookup_requires_workflow_run_event_and_success_conclusion(self):
        payload = {
            "workflow_runs": [
                {
                    "id": 1,
                    "event": "push",
                    "conclusion": "success",
                    "head_sha": "from-push",
                },
                {
                    "id": 2,
                    "event": "workflow_run",
                    "conclusion": None,
                    "head_sha": "from-none",
                },
                {
                    "id": 3,
                    "event": "workflow_run",
                    "conclusion": "failure",
                    "head_sha": "from-fail",
                },
                {
                    "id": 4,
                    "event": "workflow_run",
                    "conclusion": "success",
                    "head_sha": "from-ok",
                },
            ]
        }
        with mock.patch.object(indexnow, "github_get_json", return_value=payload):
            self.assertEqual(
                indexnow.previous_successful_workflow_head("o/r", "token"),
                "from-ok",
            )
        empty_or_invalid = {
            "workflow_runs": [
                {"id": 1, "event": "push", "conclusion": "success", "head_sha": "x"},
                {"id": 2, "event": "workflow_run", "conclusion": None, "head_sha": "y"},
            ]
        }
        with mock.patch.object(indexnow, "github_get_json", return_value=empty_or_invalid):
            self.assertIsNone(indexnow.previous_successful_workflow_head("o/r", "token"))

    def test_lookup_returns_none_when_api_empty_or_fails(self):
        with mock.patch.object(indexnow, "github_get_json", return_value={"workflow_runs": []}):
            self.assertIsNone(indexnow.previous_successful_workflow_head("o/r", "token"))
        with mock.patch.object(
            indexnow, "github_get_json", side_effect=urllib.error.URLError("nope")
        ):
            self.assertIsNone(indexnow.previous_successful_workflow_head("o/r", "token"))

    def test_main_uses_previous_workflow_sha_for_multi_commit_range(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            stdout = io.StringIO()
            env = {
                "GITHUB_TOKEN": "test-token",
                "GITHUB_REPOSITORY": "o/r",
                "GITHUB_RUN_ID": "99",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    indexnow, "previous_successful_workflow_head", return_value=shas["c1"]
                ) as lookup:
                    with mock.patch.object(indexnow.urllib.request, "urlopen") as urlopen:
                        with mock.patch.object(sys, "stdout", stdout):
                            code = indexnow.main(
                                ["--dry-run", "--repo-root", str(tmp), "--after", shas["c3"]]
                            )
            self.assertEqual(code, 0)
            urlopen.assert_not_called()
            lookup.assert_called_once()
            payload = json.loads(stdout.getvalue())
            self.assertEqual(
                payload["urlList"],
                ["https://noclaudkit.com/a/", "https://noclaudkit.com/b/"],
            )

    def test_main_falls_back_to_first_parent_when_previous_not_ancestor(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            stdout = io.StringIO()
            env = {"GITHUB_TOKEN": "test-token", "GITHUB_REPOSITORY": "o/r"}
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(
                    indexnow,
                    "previous_successful_workflow_head",
                    return_value="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                ):
                    with mock.patch.object(sys, "stdout", stdout):
                        code = indexnow.main(
                            ["--dry-run", "--repo-root", str(tmp), "--after", shas["c3"]]
                        )
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["urlList"], ["https://noclaudkit.com/b/"])

    def test_submit_still_posts_once_for_multi_commit_range(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            stderr = io.StringIO()

            class Resp:
                status = 202

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return False

                def read(self):
                    return b""

            with mock.patch.object(indexnow, "lookup_previous_successful_head", return_value=shas["c1"]):
                with mock.patch.object(indexnow.urllib.request, "urlopen", return_value=Resp()) as urlopen:
                    with mock.patch.object(sys, "stderr", stderr):
                        code = indexnow.main(
                            ["--submit", "--repo-root", str(tmp), "--after", shas["c3"]]
                        )
            self.assertEqual(code, 0)
            self.assertEqual(urlopen.call_count, 1)
            sent = json.loads(urlopen.call_args[0][0].data.decode("utf-8"))
            self.assertEqual(
                sent["urlList"],
                ["https://noclaudkit.com/a/", "https://noclaudkit.com/b/"],
            )
            self.assertEqual(stderr.getvalue().strip(), "status=202 url_count=2")

    def test_after_sha_can_come_from_indexnow_after_env(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            shas = make_multicommit_repo(tmp)
            stdout = io.StringIO()
            env = {
                "INDEXNOW_AFTER": shas["c3"],
                "GITHUB_TOKEN": "",
                "GITHUB_REPOSITORY": "",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch.object(indexnow, "lookup_previous_successful_head", return_value=None):
                    with mock.patch.object(sys, "stdout", stdout):
                        code = indexnow.main(["--dry-run", "--repo-root", str(tmp)])
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["urlList"], ["https://noclaudkit.com/b/"])


class LiveRepoTests(unittest.TestCase):
    """Sanity checks against this repository's real sitemap (no network)."""

    def test_real_sitemap_home_only(self):
        repo = ROOT.parent
        locs, _ = indexnow.parse_local_urlsets(repo)
        self.assertEqual(locs, set(HOME_URLS))

    def test_real_key_file_matches_filename(self):
        repo = ROOT.parent
        key, location = indexnow.read_key(repo)
        key_path = repo / f"{key}.txt"
        self.assertTrue(key_path.is_file())
        self.assertEqual(key_path.read_text(encoding="utf-8").strip(), key)
        self.assertEqual(location, f"https://noclaudkit.com/{key}.txt")
        self.assertNotEqual(key, FAKE_KEY)


if __name__ == "__main__":
    unittest.main()
