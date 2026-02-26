# 📘 LeetCode → GitHub Auto Sync

Automatically syncs your accepted LeetCode submissions into this GitHub repository — organized with solution files and rich README docs per problem.

**Zero cost. Runs entirely on GitHub Actions.**

---

## 📁 Project Structure

```
├── .github/workflows/sync.yml   # GitHub Actions cron + manual trigger
├── sync_leetcode.py              # Main sync script
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variable template
├── .gitignore                    # Ignores .env and cache files
├── README.md                     # You are here
└── <problem-folders>/            # Auto-generated per problem
    ├── solution.<ext>
    └── README.md
```

---

## 🚀 Quick Setup

### 1. Clone or fork this repo

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

### 2. Get your LeetCode cookies

1. Log in to [leetcode.com](https://leetcode.com) in your browser.
2. Open **DevTools → Application → Cookies → leetcode.com**.
3. Copy the values of:
   - `LEETCODE_SESSION`
   - `csrftoken` (this is the CSRF token)

### 3. Add GitHub Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name            | Value                                  |
|------------------------|----------------------------------------|
| `LEETCODE_USERNAME`    | Your LeetCode username                 |
| `LEETCODE_SESSION`     | `LEETCODE_SESSION` cookie value        |
| `LEETCODE_CSRF_TOKEN`  | `csrftoken` cookie value               |
| `LEETCODE_FETCH_LIMIT` | Number of recent submissions to fetch (e.g. `50`) |

### 4. Done!

The workflow will run **daily at 06:00 UTC** automatically.  
You can also trigger it manually: **Actions → Sync LeetCode Solutions → Run workflow**.

---

## 🖥️ Run Locally (Optional)

```bash
pip install -r requirements.txt
cp .env.example .env       # Then fill in your real values
python sync_leetcode.py
```

---

## ⚙️ How It Works

1. Fetches your recent accepted submissions from LeetCode (GraphQL API).
2. For each new problem (skips if folder already exists):
   - Fetches problem metadata (title, id, difficulty, description).
   - Fetches the submission source code.
   - Creates a folder: `{id}-{Problem-Title}/`
   - Writes `solution.<ext>` and a structured `README.md`.
3. Commits and pushes all changes automatically.

---

## 📝 Generated README Template

Each problem folder gets a README containing:

- Problem number, title, and difficulty
- Truncated problem description
- Approach placeholders (most efficient + your own)
- Complexity analysis table
- Edge cases checklist
- Full solution code block

---

## 🔒 Security

- Your `.env` file is **gitignored** and never committed.
- In GitHub Actions, credentials are stored as **encrypted repository secrets**.

---

## 📄 License

MIT — do whatever you want with it.
