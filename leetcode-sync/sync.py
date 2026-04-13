#!/usr/bin/env python3
"""
LeetCode → GitHub Sync
Fetches accepted submissions and saves them as organized solution files.
No Claude API. No README generation. Just code files that persist.
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime, timezone

# ── Config ────────────────────────────────────────────────────────────────────

USERNAME    = os.environ.get("LEETCODE_USERNAME", "").strip()
SESSION     = os.environ.get("LEETCODE_SESSION", "").strip()
CSRF        = os.environ.get("LEETCODE_CSRF_TOKEN", "").strip()
FETCH_LIMIT = int(os.environ.get("LEETCODE_FETCH_LIMIT", "50"))

if not USERNAME:
    print("❌  LEETCODE_USERNAME is not set.")
    sys.exit(1)

GQL_URL = "https://leetcode.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "Referer":      "https://leetcode.com/",
    "User-Agent":   "Mozilla/5.0 (compatible; leetcode-sync/2.0)",
    "x-csrftoken":  CSRF,
    "Cookie":       f"LEETCODE_SESSION={SESSION}; csrftoken={CSRF}",
}

# solution file extensions per language slug
EXT = {
    "python": "py", "python3": "py", "java": "java",
    "cpp": "cpp", "c": "c", "javascript": "js",
    "typescript": "ts", "go": "go", "rust": "rs",
    "kotlin": "kt", "swift": "swift", "csharp": "cs",
    "ruby": "rb", "scala": "scala", "mysql": "sql",
    "mssql": "sql", "oraclesql": "sql", "bash": "sh",
    "php": "php", "dart": "dart", "racket": "rkt",
    "erlang": "erl", "elixir": "ex",
}

# ── GraphQL helpers ───────────────────────────────────────────────────────────

def gql(query: str, variables: dict = None, retries: int = 4) -> dict:
    """POST a GraphQL query; retry with exponential backoff on failure."""
    for attempt in range(retries):
        try:
            r = requests.post(
                GQL_URL,
                json={"query": query, "variables": variables or {}},
                headers=HEADERS,
                timeout=30,
            )
            r.raise_for_status()
            body = r.json()
            if "errors" in body:
                raise ValueError(body["errors"])
            return body.get("data", {})
        except Exception as exc:
            wait = 2 ** attempt
            print(f"  ⚠  attempt {attempt+1}/{retries} failed: {exc}  — retrying in {wait}s")
            if attempt < retries - 1:
                time.sleep(wait)
    return {}   # return empty dict instead of crashing the whole run

# ── Queries ───────────────────────────────────────────────────────────────────

Q_RECENT_AC = """
query recentAC($username: String!, $limit: Int!) {
  recentAcSubmissionList(username: $username, limit: $limit) {
    id
    title
    titleSlug
    timestamp
    lang
  }
}
"""

Q_SUBMISSION_DETAIL = """
query submissionDetails($id: Int!) {
  submissionDetails(submissionId: $id) {
    code
    lang { name }
    question {
      questionFrontendId
      title
      titleSlug
      difficulty
      topicTags { name }
    }
    runtime
    memory
    runtimePercentile
    memoryPercentile
  }
}
"""

Q_PROFILE = """
query profile($username: String!) {
  matchedUser(username: $username) {
    submitStats: submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
    languageProblemCount {
      languageName
      problemsSolved
    }
  }
}
"""

# ── Core logic ────────────────────────────────────────────────────────────────

def fetch_recent_ac() -> list:
    print(f"📥  Fetching last {FETCH_LIMIT} accepted submissions for {USERNAME}…")
    data = gql(Q_RECENT_AC, {"username": USERNAME, "limit": FETCH_LIMIT})
    submissions = data.get("recentAcSubmissionList", [])
    print(f"    → {len(submissions)} submissions returned")
    return submissions


def fetch_detail(submission_id: str) -> dict:
    """Returns detail dict or {} on failure — never raises."""
    return gql(Q_SUBMISSION_DETAIL, {"id": int(submission_id)}).get("submissionDetails") or {}


def solution_path(detail: dict, lang_slug: str) -> Path:
    """
    Returns:  solutions/<difficulty>/<id>-<slug>/solution.<ext>
    """
    q        = detail.get("question", {})
    diff     = (q.get("difficulty") or "unknown").lower()
    num      = str(q.get("questionFrontendId") or "0").zfill(4)
    slug     = q.get("titleSlug") or "unknown"
    ext      = EXT.get(lang_slug.lower(), "txt")
    folder   = Path("solutions") / diff / f"{num}-{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"solution.{ext}"


def build_header(detail: dict, lang_slug: str, timestamp: int) -> str:
    q        = detail.get("question", {})
    tags     = ", ".join(t["name"] for t in q.get("topicTags", []))
    runtime  = detail.get("runtime",  "N/A")
    memory   = detail.get("memory",   "N/A")
    rt_pct   = detail.get("runtimePercentile",  0) or 0
    mem_pct  = detail.get("memoryPercentile",   0) or 0
    solved   = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d")
    url      = f"https://leetcode.com/problems/{q.get('titleSlug', '')}/"

    lang_line = f"# Language  : {lang_slug}"
    # Use '#' comment prefix for most languages; adjust for SQL/shell
    if lang_slug in ("mysql", "mssql", "oraclesql"):
        prefix = "--"
    else:
        prefix = "#"

    lines = [
        f"{prefix} {q.get('questionFrontendId', '')}. {q.get('title', '')}",
        f"{prefix} Difficulty : {q.get('difficulty', 'N/A')}",
        f"{prefix} Tags       : {tags or 'N/A'}",
        f"{prefix} Language   : {lang_slug}",
        f"{prefix} Runtime    : {runtime}  (beats {rt_pct:.1f}%)",
        f"{prefix} Memory     : {memory}  (beats {mem_pct:.1f}%)",
        f"{prefix} Solved     : {solved}",
        f"{prefix} URL        : {url}",
        "",
    ]
    return "\n".join(lines)


def save_solution(sub: dict) -> bool:
    """
    Fetch detail + save file.
    Returns True if a new file was written, False if skipped or failed.
    """
    detail = fetch_detail(sub["id"])
    if not detail:
        print(f"  ⚠  No detail returned for submission {sub['id']} ({sub['title']}) — skipping")
        return False

    lang_slug = (detail.get("lang") or {}).get("name") or sub.get("lang", "unknown")
    path = solution_path(detail, lang_slug)

    if path.exists():
        return False  # already synced

    code = detail.get("code") or ""
    if not code:
        print(f"  ⚠  Empty code for {sub['title']} — skipping")
        return False

    header  = build_header(detail, lang_slug, int(sub.get("timestamp") or 0))
    content = header + code + "\n"

    path.write_text(content, encoding="utf-8")
    print(f"  ✅  Saved: {path}")
    return True


def update_readme(profile_data: dict, synced_count: int):
    """Rewrite the top-level README with current stats. Simple, no fluff."""
    stats = {}
    for entry in (profile_data.get("submitStats") or {}).get("acSubmissionNum", []):
        stats[entry["difficulty"]] = entry["count"]

    langs = sorted(
        profile_data.get("languageProblemCount", []),
        key=lambda x: x["problemsSolved"],
        reverse=True,
    )[:5]

    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total = stats.get("All", 0)
    easy  = stats.get("Easy", 0)
    med   = stats.get("Medium", 0)
    hard  = stats.get("Hard", 0)

    lang_rows = "\n".join(
        f"| {l['languageName']} | {l['problemsSolved']} |" for l in langs
    )

    readme = f"""# 🧠 LeetCode Solutions — {USERNAME}

Auto-synced from [leetcode.com/{USERNAME}](https://leetcode.com/u/{USERNAME}/) · Last sync: `{now}`

## 📊 Stats

| Difficulty | Solved |
|------------|--------|
| **Total**  | {total} |
| Easy       | {easy} |
| Medium     | {med}  |
| Hard       | {hard} |

## 🗣️ Top Languages

| Language | Problems |
|----------|----------|
{lang_rows}

## 📁 Structure

```
solutions/
├── easy/
│   └── 0001-two-sum/
│       └── solution.py
├── medium/
└── hard/
```

Solutions are organized by difficulty, then `<id>-<slug>/solution.<ext>`.

---
*This repo is auto-generated. Do not edit manually.*
"""
    Path("README.md").write_text(readme, encoding="utf-8")
    print("📝  README.md updated")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    submissions = fetch_recent_ac()
    if not submissions:
        print("⚠  No submissions returned — possible auth issue or rate limit. Exiting cleanly.")
        sys.exit(0)   # exit 0 so the workflow doesn't show as failed

    synced = 0
    for sub in submissions:
        try:
            if save_solution(sub):
                synced += 1
            time.sleep(0.4)   # gentle rate limiting
        except Exception as exc:
            # one bad submission must never kill the whole run
            print(f"  ❌  Unexpected error on {sub.get('title')}: {exc}")
            continue

    print(f"\n🎉  Done — {synced} new solution(s) saved.")

    # Update README (best-effort; failure is non-fatal)
    try:
        profile = gql(Q_PROFILE, {"username": USERNAME}).get("matchedUser") or {}
        update_readme(profile, synced)
    except Exception as exc:
        print(f"⚠  README update skipped: {exc}")

    # Signal to the shell how many files were added (used by the workflow)
    print(f"::set-output name=synced::{synced}")


if __name__ == "__main__":
    main()
