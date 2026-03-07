---
name: flake8-compliance
description: >
  Use this agent whenever Python files under app/tools/dashboard/ have
  been created or modified. It audits every file for Flake8 violations
  (max line length 79), fixes them in-place, and confirms zero errors
  remain. Trigger explicitly with "run flake8 compliance" or
  automatically before any commit.
---

# Flake8 Compliance Agent

## Scope
All `.py` files under `app/tools/dashboard/` and `app/app.py`.

## Steps

### 1 — Discover files
Use `Glob` with pattern `app/tools/dashboard/**/*.py` (and `app/app.py`)
to get the full file list.

### 2 — Run Flake8
```bash
cd app && python -m flake8 tools/dashboard/ app.py \
  --max-line-length=79 \
  --extend-ignore=E203
```
Capture the output. If exit code is 0, report "Zero violations" and
stop.

### 3 — Parse violations
Group violations by file. For each violation note:
- File path and line number
- Error code and message
- The offending line (read the file to retrieve it)

### 4 — Fix in-place
Apply the minimum edit needed for each violation. Common patterns:

| Code | Fix strategy |
|------|-------------|
| E501 (line too long) | Break at the outermost operator or open paren; use implicit line continuation inside `()` |
| E302/E303 (blank lines) | Add or remove blank lines around function/class definitions |
| F401 (unused import) | Remove the import, or add `# noqa: F401` only if re-exported intentionally |
| W291/W293 (trailing whitespace) | Strip trailing spaces |
| E711 (comparison to None) | Replace `== None` with `is None` |
| E712 (comparison to True/False) | Replace `== True` with `is True` or plain truthiness |

When breaking a long line:
- Prefer breaking **after** an opening parenthesis so the continuation
  is naturally indented by 4 spaces.
- For string literals, use implicit concatenation:
  ```python
  msg = (
      "first part "
      "second part"
  )
  ```
- For chained method calls, break before the `.`:
  ```python
  result = (
      df.groupby("col")
      .agg(mean="mean")
      .reset_index()
  )
  ```

### 5 — Re-run Flake8
After all edits, run Flake8 again. Repeat until exit code is 0.

### 6 — Report
Summarise:
- Total violations found
- Violations fixed per file
- Any violations left (with justification if `# noqa` was used)

## Rules
- Never increase max line length beyond 79.
- Never suppress a violation with `# noqa` unless suppression is the
  only safe option (e.g. a URL that cannot be shortened).
- Do not reformat lines that were not flagged by Flake8.
- Do not add or remove docstrings unless the violation requires it.
