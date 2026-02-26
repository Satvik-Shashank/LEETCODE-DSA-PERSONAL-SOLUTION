#!/usr/bin/env python3
"""
LeetCode → GitHub Sync
Fetches accepted LeetCode submissions and commits them to this repository.
"""

import os
import re
import subprocess
import sys
import time
import html
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME", "")
LEETCODE_SESSION = os.getenv("LEETCODE_SESSION", "")
LEETCODE_CSRF_TOKEN = os.getenv("LEETCODE_CSRF_TOKEN", "")
FETCH_LIMIT = int(os.getenv("LEETCODE_FETCH_LIMIT", "50"))

GRAPHQL_URL = "https://leetcode.com/graphql"
BASE_URL = "https://leetcode.com"

LANG_EXT_MAP = {
    "python": "py", "python3": "py", "java": "java", "cpp": "cpp",
    "c": "c", "csharp": "cs", "javascript": "js", "typescript": "ts",
    "go": "go", "rust": "rs", "swift": "swift", "kotlin": "kt",
    "ruby": "rb", "scala": "scala", "php": "php", "dart": "dart",
    "racket": "rkt", "erlang": "erl", "elixir": "ex", "bash": "sh",
    "mysql": "sql", "mssql": "sql", "oraclesql": "sql",
    "postgresql": "sql", "pandas": "py",
}

HEADERS = {
    "Content-Type": "application/json",
    "Cookie": f"LEETCODE_SESSION={LEETCODE_SESSION}; csrftoken={LEETCODE_CSRF_TOKEN}",
    "x-csrftoken": LEETCODE_CSRF_TOKEN,
    "Referer": BASE_URL,
    "User-Agent": "Mozilla/5.0",
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def sanitize_folder_name(name: str) -> str:
    """Convert problem title to a clean folder name."""
    name = name.strip().replace(" ", "-")
    name = re.sub(r"[^\w\-]", "", name)
    return name


def strip_html(raw_html: str) -> str:
    """Strip HTML tags and decode entities for a readable plain-text summary."""
    text = re.sub(r"<[^>]+>", "", raw_html)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def truncate(text: str, max_len: int = 500) -> str:
    """Truncate text to max_len characters."""
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + " ..."


# ── LeetCode API ───────────────────────────────────────────────────────────────
def fetch_recent_submissions() -> list[dict]:
    """Fetch the user's recent accepted submissions via GraphQL."""
    query = """
    query recentAcSubmissions($username: String!, $limit: Int!) {
        recentAcSubmissionList(username: $username, limit: $limit) {
            id
            title
            titleSlug
            lang
            timestamp
        }
    }
    """
    payload = {
        "query": query,
        "variables": {"username": LEETCODE_USERNAME, "limit": FETCH_LIMIT},
    }
    resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", {}).get("recentAcSubmissionList", []) or []


def fetch_problem_detail(title_slug: str) -> dict:
    """Fetch problem metadata (id, difficulty, description) via GraphQL."""
    query = """
    query questionDetail($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            questionFrontendId
            title
            difficulty
            content
        }
    }
    """
    payload = {
        "query": query,
        "variables": {"titleSlug": title_slug},
    }
    resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json().get("data", {}).get("question", {})


def fetch_submission_code(submission_id: str) -> str | None:
    """Fetch the actual submitted code for a given submission id."""
    query = """
    query submissionDetails($submissionId: Int!) {
        submissionDetails(submissionId: $submissionId) {
            code
        }
    }
    """
    payload = {
        "query": query,
        "variables": {"submissionId": int(submission_id)},
    }
    resp = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    details = resp.json().get("data", {}).get("submissionDetails", {})
    return details.get("code") if details else None


# ── README Generation ──────────────────────────────────────────────────────────
def build_readme(
    problem_id: str,
    title: str,
    difficulty: str,
    description: str,
    code: str,
    lang: str,
) -> str:
    """Generate the README.md content for a problem folder."""
    ext = LANG_EXT_MAP.get(lang, lang)
    summary = truncate(strip_html(description))

    return f"""# {problem_id}. {title}

**Difficulty:** {difficulty}

---

## Problem Summary

{summary}

---

## Approach

### Most Efficient Approach

*(empty placeholder)*

### My Approach

*(empty placeholder)*

---

## Complexity Analysis

| Metric | Value |
|--------|-------|
| Time   | O(...) |
| Space  | O(...) |

*(short explanation placeholder)*

---

## Edge Cases Considered

- empty input
- duplicates
- large input

---

## Code

```{ext}
{code}
```
"""


# ── Sync Logic ─────────────────────────────────────────────────────────────────
def problem_folder_exists(problem_id: str, title: str) -> str | None:
    """Return the folder path if it already exists, else None."""
    # Check by pattern: {id}-{sanitized-title}
    folder_name = f"{problem_id}-{sanitize_folder_name(title)}"
    if os.path.isdir(folder_name):
        return folder_name
    # Also check any folder starting with the problem id
    for entry in os.listdir("."):
        if os.path.isdir(entry) and entry.startswith(f"{problem_id}-"):
            return entry
    return None


def sync():
    """Main sync routine."""
    if not LEETCODE_USERNAME or not LEETCODE_SESSION:
        print("ERROR: Set LEETCODE_USERNAME and LEETCODE_SESSION in .env or environment.")
        sys.exit(1)

    print(f"Fetching up to {FETCH_LIMIT} accepted submissions for '{LEETCODE_USERNAME}' ...")
    submissions = fetch_recent_submissions()
    if not submissions:
        print("No accepted submissions found.")
        return

    print(f"Found {len(submissions)} accepted submission(s).\n")

    # De-duplicate: keep only the latest submission per problem
    seen_slugs: dict[str, dict] = {}
    for sub in submissions:
        slug = sub["titleSlug"]
        if slug not in seen_slugs:
            seen_slugs[slug] = sub

    new_count = 0

    for sub in seen_slugs.values():
        title_slug = sub["titleSlug"]
        lang = sub["lang"]
        submission_id = sub["id"]

        # Fetch problem detail first to get the frontend id
        detail = fetch_problem_detail(title_slug)
        if not detail:
            print(f"  ⚠  Could not fetch details for '{title_slug}', skipping.")
            continue

        problem_id = detail["questionFrontendId"]
        title = detail["title"]
        difficulty = detail["difficulty"]
        description = detail.get("content", "") or ""

        # Skip if folder already exists
        existing = problem_folder_exists(problem_id, title)
        if existing:
            print(f"  ✓  [{problem_id}] {title} — already exists, skipping.")
            continue

        # Fetch submission code
        code = fetch_submission_code(submission_id)
        if not code:
            print(f"  ⚠  Could not fetch code for submission {submission_id}, skipping.")
            continue

        # Create folder and files
        folder_name = f"{problem_id}-{sanitize_folder_name(title)}"
        os.makedirs(folder_name, exist_ok=True)

        ext = LANG_EXT_MAP.get(lang, lang)
        solution_path = os.path.join(folder_name, f"solution.{ext}")
        readme_path = os.path.join(folder_name, "README.md")

        with open(solution_path, "w", encoding="utf-8") as f:
            f.write(code + "\n")

        readme_content = build_readme(problem_id, title, difficulty, description, code, lang)
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

        print(f"  ✚  [{problem_id}] {title} ({difficulty}) — synced ({lang})")
        new_count += 1

        # Be polite to the API
        time.sleep(1)

    print(f"\nDone. {new_count} new problem(s) synced.")


# ── Git Commit & Push ──────────────────────────────────────────────────────────
def git_push():
    """Stage all changes, commit, and push."""
    subprocess.run(["git", "add", "-A"], check=True)
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    if not result.stdout.strip():
        print("No changes to commit.")
        return
    subprocess.run(
        ["git", "commit", "-m", "sync: update LeetCode solutions"],
        check=True,
    )
    subprocess.run(["git", "push"], check=True)
    print("Changes pushed to GitHub.")


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sync()
    git_push()
