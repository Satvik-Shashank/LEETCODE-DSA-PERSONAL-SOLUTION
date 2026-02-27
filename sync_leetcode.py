#!/usr/bin/env python3
"""
LeetCode → GitHub Sync
Fetches accepted LeetCode submissions and commits them to this repository.
"""

import json
import os
import re
import subprocess
import sys
import time
import html
import requests
from dotenv import load_dotenv

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
LEETCODE_USERNAME = os.getenv("LEETCODE_USERNAME", "")
LEETCODE_SESSION = os.getenv("LEETCODE_SESSION", "")
LEETCODE_CSRF_TOKEN = os.getenv("LEETCODE_CSRF_TOKEN", "")
_limit = os.getenv("LEETCODE_FETCH_LIMIT", "").strip()
FETCH_LIMIT = int(_limit) if _limit else 50
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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
    """Fetch problem metadata (id, difficulty, description, topicTags) via GraphQL."""
    query = """
    query questionDetail($titleSlug: String!) {
        question(titleSlug: $titleSlug) {
            questionFrontendId
            title
            difficulty
            content
            topicTags { name slug }
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


# ── Deterministic Analysis ─────────────────────────────────────────────────────

# Tier 1: Known optimal patterns for popular LeetCode problems
KNOWN_PATTERNS: dict[str, str] = {
    "1": "Hash Map", "2": "Linked List Traversal", "3": "Sliding Window",
    "5": "Dynamic Programming", "11": "Two Pointers", "15": "Two Pointers",
    "20": "Stack", "21": "Linked List Traversal", "26": "Two Pointers",
    "27": "Two Pointers", "33": "Binary Search", "34": "Binary Search",
    "36": "Hash Map", "42": "Two Pointers", "46": "Backtracking",
    "49": "Hash Map", "53": "Kadane's Algorithm", "56": "Sorting",
    "70": "Dynamic Programming", "73": "Matrix", "75": "Two Pointers",
    "76": "Sliding Window", "78": "Backtracking", "79": "Backtracking",
    "94": "Tree Traversal", "98": "Tree Traversal", "100": "Tree Traversal",
    "101": "Tree Traversal", "102": "BFS", "104": "Tree Traversal",
    "121": "Greedy", "125": "Two Pointers", "128": "Hash Map",
    "136": "Bit Manipulation", "141": "Two Pointers", "142": "Two Pointers",
    "144": "Tree Traversal", "145": "Tree Traversal", "146": "Hash Map",
    "153": "Binary Search", "167": "Two Pointers", "169": "Boyer-Moore Voting",
    "189": "Array Reversal", "191": "Bit Manipulation", "198": "Dynamic Programming",
    "200": "BFS", "206": "Linked List Traversal", "207": "Topological Sort",
    "215": "Heap", "217": "Hash Map", "226": "Tree Traversal",
    "234": "Two Pointers", "236": "Tree Traversal", "238": "Prefix Sum",
    "242": "Hash Map", "268": "Bit Manipulation", "283": "Two Pointers",
    "287": "Two Pointers", "300": "Dynamic Programming", "322": "Dynamic Programming",
    "338": "Dynamic Programming", "347": "Heap", "371": "Bit Manipulation",
    "392": "Two Pointers", "404": "Tree Traversal", "416": "Dynamic Programming",
    "424": "Sliding Window", "435": "Greedy", "438": "Sliding Window",
    "448": "Array In-place", "494": "Dynamic Programming", "543": "Tree Traversal",
    "560": "Prefix Sum", "567": "Sliding Window", "572": "Tree Traversal",
    "647": "Dynamic Programming", "680": "Two Pointers", "695": "BFS",
    "704": "Binary Search", "724": "Prefix Sum", "733": "BFS",
    "746": "Dynamic Programming", "763": "Greedy", "844": "Two Pointers",
    "876": "Two Pointers", "977": "Two Pointers", "994": "BFS",
    "1004": "Sliding Window", "1046": "Heap", "1143": "Dynamic Programming",
    "1480": "Prefix Sum", "1492": "Math", "1528": "Sorting",
    "1920": "Array In-place", "1929": "Array Concat",
    "2095": "Linked List Traversal", "2235": "Math",
}

# Pattern → professional explanation of the most efficient approach
PATTERN_EXPLANATIONS: dict[str, str] = {
    "Hash Map": (
        "1. Create a hash map to store previously seen values.\n"
        "2. Iterate through the input in a single pass.\n"
        "3. For each element, check if the required complement/target exists in the map.\n"
        "4. If found, return the result immediately.\n"
        "5. Otherwise, add the current element to the map and continue."
    ),
    "Two Pointers": (
        "1. Initialize two pointers — one at the start and one at the end (or both at the start).\n"
        "2. Move the pointers toward each other (or in the same direction) based on a condition.\n"
        "3. At each step, compare or process the elements at both pointers.\n"
        "4. Adjust the pointer positions based on whether the condition is met.\n"
        "5. Stop when the pointers meet or cross, returning the result."
    ),
    "Binary Search": (
        "1. Initialize two pointers (low, high) covering the search range.\n"
        "2. Calculate mid = (low + high) // 2.\n"
        "3. Compare the mid element with the target.\n"
        "4. If equal, return; if target is smaller, set high = mid - 1; otherwise low = mid + 1.\n"
        "5. Repeat until the element is found or the range is exhausted."
    ),
    "Sliding Window": (
        "1. Initialize a window with two pointers (start, end) both at position 0.\n"
        "2. Expand the window by moving the end pointer to the right.\n"
        "3. When the window violates the constraint, shrink it by moving the start pointer.\n"
        "4. Track the optimal result (max/min length, sum, etc.) at each valid window state.\n"
        "5. Continue until the end pointer reaches the end of the input."
    ),
    "Dynamic Programming": (
        "1. Define the subproblem: what does dp[i] (or dp[i][j]) represent?\n"
        "2. Establish the base case(s) for the smallest subproblems.\n"
        "3. Write the recurrence relation connecting dp[i] to previously solved subproblems.\n"
        "4. Fill the DP table iteratively (bottom-up) or recursively (top-down with memoization).\n"
        "5. Return the value at the final state as the answer."
    ),
    "Stack": (
        "1. Initialize an empty stack.\n"
        "2. Iterate through the input elements one by one.\n"
        "3. For each element, check if it matches or cancels the top of the stack.\n"
        "4. If it matches, pop from the stack; otherwise push the current element.\n"
        "5. After processing all elements, the stack contains the result (or check if it's empty)."
    ),
    "BFS": (
        "1. Initialize a queue with the starting node(s) and a visited set.\n"
        "2. While the queue is not empty, dequeue the front element.\n"
        "3. Process the current element and mark it as visited.\n"
        "4. Enqueue all valid, unvisited neighbors.\n"
        "5. Continue until the queue is empty or the target is found."
    ),
    "Tree Traversal": (
        "1. Start from the root of the tree.\n"
        "2. Recursively (or iteratively) visit each node.\n"
        "3. At each node, process the value and recurse on left and right children.\n"
        "4. Combine results from subtrees as needed (e.g., height, sum, validity).\n"
        "5. Return the accumulated result."
    ),
    "Sorting": (
        "1. Sort the input array/list.\n"
        "2. Iterate through the sorted data to process elements in order.\n"
        "3. Use the sorted property to skip duplicates or merge intervals efficiently.\n"
        "4. Return the result after the single pass over sorted data."
    ),
    "Prefix Sum": (
        "1. Build a prefix sum array where prefix[i] = sum of elements from index 0 to i.\n"
        "2. Any subarray sum from index i to j can be computed as prefix[j] - prefix[i-1].\n"
        "3. Use this property to answer range-sum queries in O(1) time.\n"
        "4. For cumulative results, iterate once and accumulate running totals."
    ),
    "Greedy": (
        "1. Sort or process the input to identify the locally optimal choice at each step.\n"
        "2. At each step, make the greedy choice that looks best right now.\n"
        "3. Verify that the local optimum leads to the global optimum for this problem.\n"
        "4. Build the solution incrementally by repeating the greedy selection."
    ),
    "Backtracking": (
        "1. Start with an empty candidate solution.\n"
        "2. Try adding the next possible element to the current solution.\n"
        "3. If the solution is complete and valid, record it.\n"
        "4. If the current path cannot lead to a valid solution, backtrack (undo the last choice).\n"
        "5. Repeat for all remaining candidates."
    ),
    "Heap": (
        "1. Build a min-heap or max-heap from the input data.\n"
        "2. Extract the top element (min or max) as needed.\n"
        "3. After each extraction, the heap property is maintained automatically.\n"
        "4. Use the heap to efficiently track the k-th largest/smallest element or merge sorted lists."
    ),
    "Bit Manipulation": (
        "1. Use bitwise operations (AND, OR, XOR, shifts) to process data at the bit level.\n"
        "2. XOR can find unique elements (since x ^ x = 0 and x ^ 0 = x).\n"
        "3. Bit shifts can efficiently multiply/divide by powers of 2.\n"
        "4. Bit masking can check, set, or clear individual bits."
    ),
    "Linked List Traversal": (
        "1. Initialize pointer(s) at the head of the linked list.\n"
        "2. Traverse the list by moving the pointer(s) to the next node.\n"
        "3. Perform the required operation at each node (reverse, merge, detect cycle, etc.).\n"
        "4. Handle edge cases: empty list, single node, and the tail node.\n"
        "5. Return the modified list or the computed result."
    ),
    "Kadane's Algorithm": (
        "1. Initialize two variables: current_sum = 0, max_sum = -infinity.\n"
        "2. Iterate through the array one element at a time.\n"
        "3. At each element, set current_sum = max(element, current_sum + element).\n"
        "4. Update max_sum = max(max_sum, current_sum).\n"
        "5. After the loop, max_sum holds the maximum subarray sum."
    ),
    "Topological Sort": (
        "1. Build an adjacency list and compute in-degrees for all nodes.\n"
        "2. Add all nodes with in-degree 0 to a queue.\n"
        "3. Dequeue a node, add it to the result, and decrement in-degrees of its neighbors.\n"
        "4. If a neighbor's in-degree becomes 0, enqueue it.\n"
        "5. If all nodes are processed, return the result; otherwise a cycle exists."
    ),
    "Boyer-Moore Voting": (
        "1. Initialize a candidate and a count = 0.\n"
        "2. Iterate through the array: if count is 0, set the current element as candidate.\n"
        "3. If the current element equals the candidate, increment count; else decrement.\n"
        "4. The candidate after the full pass is the majority element."
    ),
    "Matrix": (
        "1. Iterate through the matrix row by row (and column by column if needed).\n"
        "2. Use markers or extra space to track which rows/columns need modification.\n"
        "3. Apply the modifications in a second pass to avoid overwriting data prematurely.\n"
        "4. Handle edge cases like empty matrices or single-element matrices."
    ),
    "Array In-place": (
        "1. Use the array indices themselves to encode information (e.g., mark visited elements).\n"
        "2. Iterate through the array, placing each element at its correct position.\n"
        "3. Use modular arithmetic or sign flipping to store extra data without extra space.\n"
        "4. Extract the final result from the modified array."
    ),
    "Array Concat": (
        "1. Create a new result array of the required size.\n"
        "2. Copy elements from the source array into the result.\n"
        "3. Repeat or mirror the copy as needed to fill the result.\n"
        "4. Return the constructed array."
    ),
    "Math": (
        "1. Identify the mathematical formula or pattern that governs the problem.\n"
        "2. Apply the formula directly to compute the result.\n"
        "3. Handle edge cases (zero, negative numbers, overflow) appropriately.\n"
        "4. Return the computed value."
    ),
}

# Pattern → typical time/space complexity
PATTERN_COMPLEXITY: dict[str, dict] = {
    "Hash Map":            {"time": "O(n)",       "space": "O(n)"},
    "Two Pointers":        {"time": "O(n)",       "space": "O(1)"},
    "Binary Search":       {"time": "O(log n)",   "space": "O(1)"},
    "Sliding Window":      {"time": "O(n)",       "space": "O(k)"},
    "Dynamic Programming": {"time": "O(n)",       "space": "O(n)"},
    "Stack":               {"time": "O(n)",       "space": "O(n)"},
    "BFS":                 {"time": "O(V + E)",   "space": "O(V)"},
    "Tree Traversal":      {"time": "O(n)",       "space": "O(h)"},
    "Sorting":             {"time": "O(n log n)", "space": "O(1)"},
    "Prefix Sum":          {"time": "O(n)",       "space": "O(n)"},
    "Greedy":              {"time": "O(n log n)", "space": "O(1)"},
    "Backtracking":        {"time": "O(2^n)",     "space": "O(n)"},
    "Heap":                {"time": "O(n log k)", "space": "O(k)"},
    "Bit Manipulation":    {"time": "O(n)",       "space": "O(1)"},
    "Linked List Traversal":{"time": "O(n)",      "space": "O(1)"},
    "Kadane's Algorithm":  {"time": "O(n)",       "space": "O(1)"},
    "Topological Sort":    {"time": "O(V + E)",   "space": "O(V)"},
    "Boyer-Moore Voting":  {"time": "O(n)",       "space": "O(1)"},
    "Matrix":              {"time": "O(m × n)",   "space": "O(1)"},
    "Array In-place":      {"time": "O(n)",       "space": "O(1)"},
    "Array Concat":        {"time": "O(n)",       "space": "O(n)"},
    "Math":                {"time": "O(1)",       "space": "O(1)"},
}

# LeetCode topic tag slug → pattern name
TAG_TO_PATTERN: dict[str, str] = {
    "hash-table": "Hash Map", "two-pointers": "Two Pointers",
    "binary-search": "Binary Search", "sliding-window": "Sliding Window",
    "dynamic-programming": "Dynamic Programming", "stack": "Stack",
    "breadth-first-search": "BFS", "depth-first-search": "Tree Traversal",
    "tree": "Tree Traversal", "binary-tree": "Tree Traversal",
    "sorting": "Sorting", "prefix-sum": "Prefix Sum",
    "greedy": "Greedy", "backtracking": "Backtracking",
    "heap-priority-queue": "Heap", "bit-manipulation": "Bit Manipulation",
    "linked-list": "Linked List Traversal", "graph": "BFS",
    "topological-sort": "Topological Sort", "math": "Math",
    "matrix": "Matrix", "recursion": "Backtracking",
    "divide-and-conquer": "Binary Search", "binary-search-tree": "Binary Search",
    "monotonic-stack": "Stack", "queue": "BFS",
}

# Code heuristic rules: (regex pattern, detected pattern name)
CODE_HEURISTICS: list[tuple[str, str]] = [
    (r"\bheapq\b|\bheappush\b|\bheappop\b|\bPriorityQueue\b", "Heap"),
    (r"\bdeque\b|\bBFS\b|\bbfs\b", "BFS"),
    (r"\bsorted\s*\(|\.\.sort\s*\(", "Sorting"),
    (r"\bstack\b.*\b(append|push)\b|\bstack\.pop\b", "Stack"),
    (r"\bmid\s*=.*//\s*2|lo\s*\+\s*hi|left\s*\+\s*right.*//\s*2|bisect", "Binary Search"),
    (r"\b(left|lo|l)\b.*\b(right|hi|r)\b.*while", "Two Pointers"),
    (r"while.*left.*<.*right|while.*lo.*<.*hi", "Two Pointers"),
    (r"\bdefaultdict\b|\bCounter\b|\bcollections\.", "Hash Map"),
    (r"\bdict\s*\(\)|\{\}|\bhash|\bseen\b|\blookup\b", "Hash Map"),
    (r"\bprefix\b|\bcumsum\b|running.*sum|cumulative", "Prefix Sum"),
    (r"\bdp\[|\bdp\s*=|\bmemo\[|@lru_cache|@cache", "Dynamic Programming"),
    (r"\bdef\s+\w+.*\(.*\).*:\s*\n.*\1", "Backtracking"),
    (r"\b(node|head|ListNode)\b.*\.next", "Linked List Traversal"),
    (r"\b(root|TreeNode)\b.*\.(left|right)", "Tree Traversal"),
    (r"\b(\^|xor|XOR|\|\||\&\&|<<|>>)\b", "Bit Manipulation"),
]


def _detect_pattern_from_code(code: str) -> str | None:
    """Tier 2: Scan the code for heuristic patterns."""
    for pattern_re, pattern_name in CODE_HEURISTICS:
        if re.search(pattern_re, code, re.IGNORECASE | re.DOTALL):
            return pattern_name
    return None


def _detect_pattern_from_tags(topic_tags: list[dict]) -> str | None:
    """Tier 3: Map LeetCode topic tags to a known pattern."""
    # Prefer more specific tags first (they appear later in the tag list)
    for tag in reversed(topic_tags):
        slug = tag.get("slug", "")
        if slug in TAG_TO_PATTERN:
            return TAG_TO_PATTERN[slug]
    return None


def _analyze_my_approach(code: str, lang: str) -> str:
    """Generate a step-by-step description of what the user's code does."""
    steps: list[str] = []

    # Detect data structures
    if re.search(r"\bdict\b|\bdefaultdict\b|\bCounter\b|\{\}", code):
        steps.append("Initialize a hash map / dictionary to store values.")
    if re.search(r"\bset\s*\(|\{.*\}", code) and not re.search(r"\{.*:.*\}", code):
        steps.append("Use a set to track unique elements.")
    if re.search(r"\[\]|\blist\s*\(", code):
        steps.append("Create a list/array to store intermediate results.")
    if re.search(r"\bstack\b", code, re.IGNORECASE):
        steps.append("Use a stack for LIFO processing.")
    if re.search(r"\bdeque\b|\bqueue\b", code, re.IGNORECASE):
        steps.append("Use a queue/deque for BFS-style processing.")

    # Detect operations
    if re.search(r"\bsorted\b|\.\.sort\b", code):
        steps.append("Sort the input data.")
    if re.search(r"for .+ in .+:", code):
        loop_count = len(re.findall(r"for .+ in .+:", code))
        if loop_count >= 2 and re.search(r"for .+ in .+:.*\n\s+for .+ in .+:", code, re.DOTALL):
            steps.append("Use nested loops to compare/process element pairs.")
        else:
            steps.append(f"Iterate through the input ({loop_count} loop{'s' if loop_count > 1 else ''}).")
    elif re.search(r"while ", code):
        steps.append("Use a while loop to traverse/process the data.")
    if re.search(r"\bif\b.*\breturn\b|\bif\b.*\bbreak\b", code):
        steps.append("Check conditions to find the answer or terminate early.")
    if re.search(r"\bappend\b|\bextend\b|\+\=", code):
        steps.append("Build the result by appending/accumulating values.")
    if re.search(r"\breturn\b", code):
        steps.append("Return the final result.")

    if not steps:
        steps = ["Process the input and compute the result.", "Return the answer."]

    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))


def _estimate_complexity(code: str) -> tuple[str, str, str]:
    """Heuristic complexity estimation based on code structure."""
    # Count loop nesting depth
    lines = code.split("\n")
    max_loop_depth = 0
    current_depth = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"(for |while )", stripped):
            current_depth += 1
            max_loop_depth = max(max_loop_depth, current_depth)
        elif stripped and not stripped.startswith("#") and current_depth > 0:
            # Rough heuristic: if indentation decreases, we left a loop
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                current_depth = 0

    # Detect sorting
    has_sort = bool(re.search(r"\bsorted\b|\.\.sort\b", code))
    # Detect extra data structures
    has_extra_ds = bool(re.search(
        r"\bdict\b|\bdefaultdict\b|\bCounter\b|\bset\b|\[\]|\blist\s*\(|\bdeque\b",
        code
    ))
    has_recursion = bool(re.search(r"\bdef\s+(\w+).*\n(?:.*\n)*?.*\b\1\(", code))

    # Determine time complexity
    if has_recursion and re.search(r"dp\[|memo\[|@cache|@lru_cache", code):
        time_c = "O(n)"
        explanation = "Dynamic programming with memoization ensures each subproblem is solved once."
    elif has_recursion:
        time_c = "O(2^n)"
        explanation = "Recursive branching without memoization leads to exponential time."
    elif has_sort:
        time_c = "O(n log n)"
        explanation = "Dominated by the sorting step."
    elif max_loop_depth >= 3:
        time_c = "O(n³)"
        explanation = f"Triple-nested loops over the input ({max_loop_depth} levels deep)."
    elif max_loop_depth == 2:
        time_c = "O(n²)"
        explanation = "Nested loops iterate over the input."
    elif max_loop_depth == 1:
        time_c = "O(n)"
        explanation = "Single pass through the input."
    else:
        time_c = "O(1)"
        explanation = "Constant-time operations with no loops."

    # Determine space complexity
    space_c = "O(n)" if has_extra_ds else "O(1)"
    if has_extra_ds:
        explanation += " Extra space is used for auxiliary data structures."
    else:
        explanation += " No significant extra space is used."

    return time_c, space_c, explanation


def analyze_problem(
    problem_id: str,
    title: str,
    difficulty: str,
    description: str,
    code: str,
    lang: str,
    topic_tags: list[dict],
) -> dict:
    """4-tier analysis: known patterns → code heuristics → topic tags → Gemini AI.

    Always returns a complete analysis dict (never None).
    """
    source = ""

    # Tier 1: Known problem dictionary
    pattern = KNOWN_PATTERNS.get(problem_id)
    if pattern:
        source = "known-pattern"

    # Tier 2: Code heuristic detection
    if not pattern:
        pattern = _detect_pattern_from_code(code)
        if pattern:
            source = "code-heuristic"

    # Tier 3: LeetCode topic tags
    if not pattern:
        pattern = _detect_pattern_from_tags(topic_tags)
        if pattern:
            source = "topic-tags"

    # Build deterministic result if pattern was found
    if pattern:
        explanation = PATTERN_EXPLANATIONS.get(pattern, f"Use the {pattern} technique to solve this efficiently.")
        complexity = PATTERN_COMPLEXITY.get(pattern, {"time": "O(n)", "space": "O(n)"})
        my_approach = _analyze_my_approach(code, lang)
        time_c, space_c, comp_expl = _estimate_complexity(code)

        print(f"  📊 Pattern detected: {pattern} (via {source})")
        return {
            "most_efficient_approach": f"**Pattern: {pattern}**\n\n{explanation}",
            "my_approach": my_approach,
            "time_complexity": time_c,
            "space_complexity": space_c,
            "complexity_explanation": comp_expl,
        }

    # Tier 4: Gemini AI (optional fallback for unknown patterns)
    ai_result = _analyze_with_gemini(title, difficulty, description, code, lang)
    if ai_result:
        return ai_result

    # Final fallback: use heuristic complexity even without a pattern
    my_approach = _analyze_my_approach(code, lang)
    time_c, space_c, comp_expl = _estimate_complexity(code)
    return {
        "most_efficient_approach": "*(Pattern not auto-detected — review and update manually)*",
        "my_approach": my_approach,
        "time_complexity": time_c,
        "space_complexity": space_c,
        "complexity_explanation": comp_expl,
    }


# ── AI Analysis (Tier 4 — optional) ───────────────────────────────────────────
MAX_RETRIES = 2
RETRY_DELAY = 30  # seconds


def _analyze_with_gemini(
    title: str,
    difficulty: str,
    description: str,
    code: str,
    lang: str,
) -> dict | None:
    """Optional Tier 4: Use Gemini AI for richer analysis when API key is set."""
    if not HAS_GENAI or not GEMINI_API_KEY:
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""You are a DSA expert. Respond with ONLY a JSON object (no fences) with these keys:
1. "most_efficient_approach": step-by-step optimal algorithm (4-8 numbered steps)
2. "my_approach": step-by-step description of the user's code (4-8 numbered steps)
3. "time_complexity": Big-O time of user's code
4. "space_complexity": Big-O space of user's code
5. "complexity_explanation": 1-2 sentence explanation

Problem: {title} ({difficulty})
Description: {strip_html(description)[:1000]}

User's code ({lang}):
{code}
"""

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            result = json.loads(raw)
            required = ["most_efficient_approach", "my_approach",
                        "time_complexity", "space_complexity", "complexity_explanation"]
            if all(k in result for k in required):
                print("  🤖 AI analysis complete")
                return result
            return None

        except Exception as exc:  # noqa: BLE001
            if "429" in str(exc) and attempt < MAX_RETRIES:
                print(f"  ⏳ AI rate limited, retrying in {RETRY_DELAY}s...")
                time.sleep(RETRY_DELAY)
                continue
            return None

    return None


# ── README Generation ──────────────────────────────────────────────────────────
def build_readme(
    problem_id: str,
    title: str,
    difficulty: str,
    description: str,
    code: str,
    lang: str,
    analysis: dict | None = None,
) -> str:
    """Generate the README.md content for a problem folder."""
    ext = LANG_EXT_MAP.get(lang, lang)
    summary = truncate(strip_html(description))

    # Fallback values
    most_efficient = "*(empty placeholder)*"
    my_approach = "*(empty placeholder)*"
    time_comp = "O(...)"
    space_comp = "O(...)"
    comp_explanation = "*(short explanation placeholder)*"

    if analysis:
        most_efficient = analysis.get("most_efficient_approach", most_efficient)
        my_approach = analysis.get("my_approach", my_approach)
        time_comp = analysis.get("time_complexity", time_comp)
        space_comp = analysis.get("space_complexity", space_comp)
        comp_explanation = analysis.get("complexity_explanation", comp_explanation)

    return f"""# {problem_id}. {title}

**Difficulty:** {difficulty}

---

## Problem Summary

{summary}

---

## Approach

### Most Efficient Approach

{most_efficient}

### My Approach

{my_approach}

---

## Complexity Analysis

| Metric | Value |
|--------|-------|
| Time   | {time_comp} |
| Space  | {space_comp} |

{comp_explanation}

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
        topic_tags = detail.get("topicTags", []) or []

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

        # 4-tier analysis (deterministic first, AI optional)
        analysis = analyze_problem(problem_id, title, difficulty, description, code, lang, topic_tags)

        readme_content = build_readme(problem_id, title, difficulty, description, code, lang, analysis)
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
    # Pull remote changes first, then push
    subprocess.run(["git", "pull", "--rebase"], check=True)
    subprocess.run(["git", "push"], check=True)
    print("Changes pushed to GitHub.")


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sync()
    git_push()
