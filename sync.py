"""
sync.py — LeetCode Auto-Sync Utility
=====================================
Repository : https://github.com/Satvik-Shashank/LEETCODE-DSA-PERSONAL-SOLUTION
Local root : C:\\Users\\janga\\OneDrive\\Documents\\LEETCODE DSA
Author     : Satvik-Shashank
Usage      : python sync.py

Behaviour
---------
1. Verify git is installed and repo is initialised.
2. Run `git status --porcelain` to detect staged/unstaged changes.
3. If nothing changed → exit gracefully.
4. `git add .`
5. Detect the latest-modified .py / .java / .cpp solution file.
6. Build a clean commit message from the filename.
7. `git commit -m "<message>"`
8. `git push origin main`
9. Print a clear summary at every step.

Constraints
-----------
- No LeetCode API, GitHub API, OAuth, tokens, secrets, or cloud services.
- No third-party Python packages (stdlib only).
- Safe if git not initialised, remote missing, or internet unavailable.
- Cross-platform (Windows, macOS, Linux).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────
# CONFIGURATION — adjust only if paths change
# ─────────────────────────────────────────────

REPO_ROOT = Path(r"C:\Users\janga\OneDrive\Documents\LEETCODE DSA")
REMOTE    = "origin"
BRANCH    = "main"

# Extensions considered "solution files" for commit-message generation.
SOLUTION_EXTENSIONS = {".py", ".java", ".cpp", ".c", ".js", ".ts"}

# Directories that hold actual solutions (used only for smart message detection).
SOLUTION_DIRS = {"Easy", "Medium", "Hard"}

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────

def log(emoji: str, message: str) -> None:
    """Pretty-print a log line."""
    print(f"  {emoji}  {message}")


def run(cmd: list[str], *, cwd: Path, capture: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command safely.

    Returns the CompletedProcess object.
    Raises SystemExit with a clear message on CalledProcessError only when
    the caller decides to propagate (via check=True).
    """
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=capture,
        text=True,
    )


# ─────────────────────────────────────────────
# STEP 0 — Pre-flight checks
# ─────────────────────────────────────────────

def check_git_installed() -> None:
    """Abort early if git is not on PATH."""
    result = run(["git", "--version"], cwd=REPO_ROOT)
    if result.returncode != 0:
        log("❌", "git is not installed or not on PATH.")
        log("💡", "Install git from https://git-scm.com and retry.")
        sys.exit(1)
    log("✅", f"git found  →  {result.stdout.strip()}")


def check_repo_initialised() -> None:
    """Abort if the local folder is not a git repository."""
    git_dir = REPO_ROOT / ".git"
    if not git_dir.is_dir():
        log("❌", f"No git repository found at: {REPO_ROOT}")
        log("💡", "Run the first-time setup commands in README.md and retry.")
        sys.exit(1)
    log("✅", f"Repository root  →  {REPO_ROOT}")


def check_remote_exists() -> bool:
    """Return True if 'origin' remote is configured."""
    result = run(["git", "remote", "get-url", REMOTE], cwd=REPO_ROOT)
    if result.returncode != 0:
        log("⚠️ ", f"Remote '{REMOTE}' is not configured. Push will be skipped.")
        return False
    log("✅", f"Remote '{REMOTE}'  →  {result.stdout.strip()}")
    return True


# ─────────────────────────────────────────────
# STEP 1 — Detect changes
# ─────────────────────────────────────────────

def get_changed_files() -> list[str]:
    """
    Return list of changed file paths reported by `git status --porcelain`.
    Includes untracked (??) and modified/added (M, A, etc.) files.
    """
    result = run(["git", "status", "--porcelain"], cwd=REPO_ROOT)
    if result.returncode != 0:
        log("❌", "git status failed.")
        log("🔍", result.stderr.strip())
        sys.exit(1)

    lines = result.stdout.strip().splitlines()
    changed = []
    for line in lines:
        # Format: "XY filename" — first two chars are status codes.
        if len(line) > 3:
            filepath = line[3:].strip()
            # Handle renames: "old -> new"
            if " -> " in filepath:
                filepath = filepath.split(" -> ")[-1]
            changed.append(filepath)
    return changed


# ─────────────────────────────────────────────
# STEP 2 — Stage all changes
# ─────────────────────────────────────────────

def stage_all() -> None:
    result = run(["git", "add", "."], cwd=REPO_ROOT)
    if result.returncode != 0:
        log("❌", "git add failed.")
        log("🔍", result.stderr.strip())
        sys.exit(1)
    log("✅", "All changes staged.")


# ─────────────────────────────────────────────
# STEP 3 — Build commit message
# ─────────────────────────────────────────────

def filename_to_commit_message(filepath: str) -> str:
    """
    Convert a solution filepath to a clean commit message.

    Examples
    --------
    Easy/Arrays/1_Two_Sum.py
        → "Add LeetCode: 1 Two Sum"

    Medium/Binary_Search/33_Search_in_Rotated_Sorted_Array.py
        → "Add LeetCode: 33 Search In Rotated Sorted Array"

    Hard/DP/72_Edit_Distance.java
        → "Add LeetCode: 72 Edit Distance"
    """
    stem = Path(filepath).stem          # e.g. "1_Two_Sum"
    # Replace underscores with spaces, then title-case each word.
    readable = stem.replace("_", " ").title()
    return f"Add LeetCode: {readable}"


def pick_best_file(changed: list[str]) -> str | None:
    """
    From the list of changed files, return the most recently modified
    solution file inside Easy/, Medium/, or Hard/.

    Falls back to the first solution-extension file if none match the
    directory filter.  Returns None if no solution file is detected.
    """
    solution_candidates = [
        f for f in changed
        if Path(f).suffix.lower() in SOLUTION_EXTENSIONS
    ]
    if not solution_candidates:
        return None

    # Prefer files inside recognised solution directories.
    preferred = [
        f for f in solution_candidates
        if Path(f).parts[0] in SOLUTION_DIRS
    ]
    pool = preferred if preferred else solution_candidates

    # Pick the file with the latest mtime on disk.
    def mtime(rel: str) -> float:
        abs_path = REPO_ROOT / rel
        try:
            return abs_path.stat().st_mtime
        except FileNotFoundError:
            return 0.0

    return max(pool, key=mtime)


def build_commit_message(changed: list[str]) -> str:
    """
    Return the best commit message for the current batch of changes.
    Falls back to a generic message when no solution file is found.
    """
    best = pick_best_file(changed)
    if best:
        msg = filename_to_commit_message(best)
        log("📝", f"Detected solution file  →  {best}")
        log("💬", f"Commit message          →  {msg}")
        return msg

    # Generic fallback (e.g. only README or .gitignore changed).
    log("📝", "No solution file detected — using generic commit message.")
    return "Update LeetCode repository"


# ─────────────────────────────────────────────
# STEP 4 — Commit
# ─────────────────────────────────────────────

def commit(message: str) -> None:
    result = run(["git", "commit", "-m", message], cwd=REPO_ROOT)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        # git prints "nothing to commit" on stdout even with returncode 1
        # when the working tree is clean after `git add .` found nothing new.
        combined = (stdout + stderr).lower()
        if "nothing to commit" in combined:
            log("ℹ️ ", "Nothing new to commit (working tree clean).")
            sys.exit(0)
        log("❌", "git commit failed.")
        log("🔍", stderr or stdout)
        sys.exit(1)
    log("✅", "Commit created.")


# ─────────────────────────────────────────────
# STEP 5 — Push
# ─────────────────────────────────────────────

def push() -> None:
    log("🚀", f"Pushing to {REMOTE}/{BRANCH} …")
    result = run(["git", "push", REMOTE, BRANCH], cwd=REPO_ROOT, capture=False)
    if result.returncode != 0:
        log("❌", "git push failed.")
        log("💡", "Check your SSH key / internet connection and retry.")
        sys.exit(1)
    log("✅", "Push successful.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main() -> None:
    print()
    print("=" * 52)
    print("   🔄  LeetCode Auto-Sync  —  sync.py")
    print("=" * 52)
    print()

    # ── Pre-flight ──────────────────────────
    check_git_installed()
    check_repo_initialised()
    has_remote = check_remote_exists()
    print()

    # ── Detect changes ──────────────────────
    log("🔍", "Scanning for changes …")
    changed = get_changed_files()

    if not changed:
        log("💤", "No new or modified files found.  Nothing to sync.")
        print()
        print("=" * 52)
        sys.exit(0)

    log("📂", f"{len(changed)} file(s) changed:")
    for f in changed:
        print(f"        • {f}")
    print()

    # ── Stage ───────────────────────────────
    stage_all()

    # ── Commit message ──────────────────────
    message = build_commit_message(changed)
    print()

    # ── Commit ──────────────────────────────
    commit(message)

    # ── Push ────────────────────────────────
    if has_remote:
        print()
        push()
    else:
        log("⚠️ ", "Skipping push — no remote configured.")

    print()
    print("=" * 52)
    print("   ✅  Sync complete!")
    print("=" * 52)
    print()


if __name__ == "__main__":
    main()
