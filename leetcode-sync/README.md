# 🧠 LeetCode Solutions — Satvik_Janga

Auto-synced from LeetCode via GitHub Actions. No Claude API. No external services. Just works.

---

## ⚡ Setup (5 minutes)

### 1. Create a new GitHub repo and push this folder

```bash
git init
git remote add origin https://github.com/<your-username>/<repo-name>.git
git add -A
git commit -m "init: leetcode sync"
git push -u origin main
```

### 2. Get your LeetCode cookies

1. Log in at [leetcode.com](https://leetcode.com)
2. Open **DevTools** (F12) → **Application** → **Cookies** → `https://leetcode.com`
3. Copy:
   - `LEETCODE_SESSION` — long token starting with `eyJ...`
   - `csrftoken` — shorter alphanumeric string

> Cookies expire roughly every 2–4 weeks. When the sync fails, just refresh them.

### 3. Add GitHub Secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name            | Value                          |
|------------------------|--------------------------------|
| `LEETCODE_USERNAME`    | `Satvik_Janga`                 |
| `LEETCODE_SESSION`     | your `LEETCODE_SESSION` cookie |
| `LEETCODE_CSRF_TOKEN`  | your `csrftoken` cookie        |

### 4. Enable Actions

Go to **Actions** tab → click **"I understand my workflows, go ahead and enable them"** if prompted.

That's it. The workflow runs **daily at 06:00 UTC** automatically.  
To trigger immediately: **Actions → Sync LeetCode Solutions → Run workflow**.

---

## 🗂️ File Structure

```
solutions/
├── easy/
│   └── 0001-two-sum/
│       └── solution.py
├── medium/
│   └── 0002-add-two-numbers/
│       └── solution.cpp
└── hard/
    └── 0004-median-of-two-sorted-arrays/
        └── solution.java
```

Each `solution.<ext>` has a header comment with difficulty, tags, runtime, memory, and the LeetCode URL.

---

## 🖥️ Run Locally

```bash
pip install requests
cp .env.example .env       # fill in your cookies
python sync.py
```

---

## 🔄 How the Sync Works

1. Calls LeetCode's GraphQL API to fetch your last N accepted submissions
2. For each submission not already saved locally:
   - Fetches the source code and problem metadata
   - Saves `solutions/<difficulty>/<id>-<slug>/solution.<ext>`
3. Updates `README.md` with your current stats
4. Commits and pushes — only if something actually changed

### Why it won't break

- Every network call has **4 retries with exponential backoff**
- A single failed submission is **skipped, not fatal** — the rest still save
- If LeetCode returns nothing (rate limit / downtime), the script **exits cleanly** with code 0 so GitHub doesn't spam you with failure emails
- The workflow only commits when there are actual file changes

---

## 🔑 Cookie Rotation (when sync stops working)

LeetCode session cookies expire. When that happens:

1. Log in to LeetCode, grab fresh cookies (same steps as setup)
2. Go to repo **Settings → Secrets** and update `LEETCODE_SESSION` and `LEETCODE_CSRF_TOKEN`
3. Trigger a manual run from the Actions tab

---

## 📄 License

MIT
