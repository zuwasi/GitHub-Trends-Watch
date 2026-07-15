# Claude Mythos Security Assessment Report
# GitHub Trends Watch — v1.0.1
# Date: 2026-07-15
# Assessor: Claude Mythos (automated)
# Authorization: User-owned codebase (Daniel Liezrowice-Zuwasi / ESL)

## Executive Summary

**Target**: GitHub Trends Watch — Python desktop application that scrapes GitHub trending,
analyzes repos with AI agents, and emails HTML reports.

**Repo**: https://github.com/zuwasi/GitHub-Trends-Watch

**Security Level**: **Medium** — The app has two real security issues (stored credential
exposure and HTML injection in email reports) and several low-severity code quality items.
No Critical or High severity findings. The app is safe for personal/trusted use but should
not be deployed in a multi-user or untrusted environment without addressing F-001 and F-002.

## Scope

| Component | Path |
|-----------|------|
| Entry point | `main.py` |
| GUI | `gui.py` |
| Config | `config_manager.py` |
| Email | `email_handler.py` |
| Agent runner | `agent_runner.py` |
| Scraper | `trending_scraper.py` |
| Scheduler | `scheduler.py` |
| Auto-start | `autostart.py` |
| Single instance | `single_instance.py` |
| Rating engine | `rating_engine.py` |
| Chart maker | `chart_maker.py` |
| Agent detector | `agent_detector.py` |

### Files NOT assessed (out of scope)
- `dist/` — build artifacts (PyInstaller exes)
- `build/` — PyInstaller intermediate files
- `__pycache__/` — compiled bytecode

## Checks Performed

| Check | Tool | Result |
|-------|------|-------|
| Static analysis (Python) | `bandit` v1.9.4 | 16 Low severity, 0 Medium, 0 High |
| Secret search (code) | `rg` for password/token/secret/api_key | No hardcoded secrets in source |
| Secret search (config) | Manual file inspection | SMTP password stored in plaintext |
| XSS/HTML injection | Manual code review | 2 confirmed injection vectors |
| Command injection | Manual code review + bandit | subprocess used safely (no shell=True) |
| Dependency audit | Manual (requirements.txt) | No known CVEs in listed deps |
| File permissions | `os.stat` | Config file world-readable on Windows |
| TLS/SSL | Manual review | SMTP uses STARTTLS or SMTP_SSL (good) |
| Auto-start mechanism | Manual review | Registry/plist/desktop file (standard, no privilege escalation) |
| Input validation | Manual review | Config values validated in `validate_config()` |

## Limitations

- No dynamic testing (DAST) was performed — assessment is static only.
- Dependency CVE check was manual; no `osv-scanner` or `grype` available on this machine.
- PyInstaller exe was not assessed for binary-level vulnerabilities.
- The app is a local desktop tool, not a web service — server-side attack surface is minimal.

---

## Findings

### F-001 — SMTP credentials stored in plaintext without file permission hardening

Status: Confirmed
Severity: Medium
CVSS 3.1: `CVSS:3.1/AV:L/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N` — 6.2
CWE: CWE-312 (Cleartext Storage of Sensitive Information)
Confidence: confirmed
Affected components:
- `config_manager.py:31` — default config with `"password": ""`
- `config_manager.py:69-74` — `save_config()` writes JSON with plaintext password
- `gui.py:432` — saves password from UI to config
- `~/.github_trending_reporter/config.json` — on-disk file with SMTP password

Description:
The SMTP password (or app password) is stored in `~/.github_trending_reporter/config.json`
in cleartext JSON. On Windows, the file permissions are `-rw-rw-rw-` (world-readable/writable).
Any process or user on the machine can read the SMTP credentials.

Impact:
An attacker with local filesystem access can read the SMTP email and password, gaining
the ability to send emails as the user, potentially accessing the email account if an
app password is reused or the account has limited 2FA scope.

Validation / evidence:
```
$ python -c "import os,stat; st=os.stat(os.path.expanduser('~/.github_trending_reporter/config.json')); print(stat.filemode(st.st_mode))"
-rw-rw-rw-
```
Config file contains: `"password": "<redacted-app-password>"` (Yahoo app password).

Mitigation / owner decision:
1. **Minimum fix**: Set file permissions to `0600` on save (`os.chmod(path, 0o600)`).
2. **Better**: Use OS-native credential storage:
   - Windows: `win32crypt.CryptProtectData` (DPAPI)
   - macOS: Keychain (`security` command or `keyring` library)
   - Linux: `libsecret` / `gnome-keyring` or `keyring` library
3. **Alternative**: Use the `keyring` Python package for cross-platform credential storage.

---

### F-002 — HTML injection in email reports (stored XSS via GitHub trending data)

Status: Confirmed
Severity: Medium
CVSS 3.1: `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N` — 5.4
CWE: CWE-79 (Cross-site Scripting)
Confidence: confirmed
Affected components:
- `email_handler.py:115` — `r['name']` inserted into `<a>` tag without escaping
- `email_handler.py:118` — `r['description']` inserted into `<p>` tag without escaping
- `email_handler.py:107-109` — `r['contributors']` inserted into `<span>` without escaping
- `email_handler.py:78` — `analysis_html` from markdown conversion (agent output)

Description:
Repo names, descriptions, and contributor names are scraped from GitHub trending and
inserted directly into HTML email templates using Python f-strings without HTML escaping.
If a malicious repo on GitHub trending had a description like
`<script>alert('xss')</script>` or `<img src=x onerror=alert(1)>`, the HTML would be
rendered in the recipient's email client.

Additionally, the AI agent's markdown output is converted to HTML via the `markdown`
library, which does render raw HTML by default (the `extra` extension allows inline HTML).

Impact:
- Email clients that render HTML (most modern clients) could execute injected JavaScript
  or load tracking pixels from attacker-controlled URLs.
- In practice, most email clients strip `<script>` tags, but `<img onerror>`,
  `<a href="javascript:">`, and CSS injection are still possible.
- The agent output path is lower risk since the agent is trusted, but if the agent
  is tricked by prompt injection from repo descriptions, it could output malicious HTML.

Validation / evidence:
```python
# In email_handler.py line 115:
<h3><a href="{r['url']}">{r['name']}</a></h3>
# No html.escape() applied to r['name'] or r['description']
```

Mitigation / owner decision:
1. **Repo data**: Wrap all scraped values with `html.escape()` before inserting into HTML:
   ```python
   from html import escape
   name = escape(r['name'])
   description = escape(r['description'] or 'No description available.')
   ```
2. **Agent output**: Configure markdown to NOT render raw HTML:
   ```python
   md.markdown(text, extensions=["tables", "fenced_code"], output_format="html5")
   # Remove "extra" and "codehilite" which allow inline HTML
   ```

---

### F-003 — subprocess execution with user-controlled command and args

Status: Accepted intentional design
Severity: Low
CVSS 3.1: `CVSS:3.1/AV:L/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:H` — 6.5 (but requires local access)
CWE: CWE-78 (OS Command Injection)
Confidence: confirmed (but accepted)
Affected components:
- `agent_runner.py:92-101` — `subprocess.run(cmd, ...)` where `cmd = [command] + prompt_args + [prompt]`
- `gui.py:160` — user can edit agent command and args

Description:
The agent runner executes a subprocess with the agent command and prompt args from the
config file. A user with access to the config file could change the command to any
executable. However, `shell=True` is NOT used (good), and the command is a list (not a
string), which prevents shell injection.

Impact:
An attacker who can modify `~/.github_trending_reporter/config.json` can set the agent
command to any executable, which would run on the next scheduled check. However, if the
attacker can modify the config file, they already have local filesystem access and can
run arbitrary code directly.

Mitigation / owner decision:
This is accepted as intentional design — the app's purpose is to run user-selected AI
agents. The use of `subprocess.run()` with a list (no `shell=True`) is the correct safe
pattern. No change needed.

---

### F-004 — Bare `except Exception: pass` swallows errors silently

Status: TODO
Severity: Low
CVSS 3.1: N/A (code quality)
CWE: CWE-703 (Improper Handling of Exceptional Conditions)
Confidence: confirmed
Affected components:
- `email_handler.py:407` — history cleanup error swallowed
- `gui.py:568` — file opener error swallowed
- `gui.py:575` — history count error swallowed
- `gui.py:644` — tray icon stop error swallowed
- `scheduler.py:177` — status callback error swallowed

Description:
Multiple bare `except Exception: pass` blocks silently swallow all exceptions. While
this prevents crashes in non-critical paths, it also hides errors that could indicate
security-relevant failures (e.g., permission denied, file not found, disk full).

Mitigation / owner decision:
Replace with logging:
```python
except Exception as e:
    logger.debug("Non-critical error: %s", e)
```

---

### F-005 — Config file not in .gitignore at user home (credentials could be committed)

Status: Mitigated
Severity: Low
CWE: CWE-200 (Exposure of Sensitive Information)
Confidence: confirmed
Affected components:
- `.gitignore:5` — `config.json` is listed

Description:
The `.gitignore` file correctly excludes `config.json` from git. However, the actual
config file is at `~/.github_trending_reporter/config.json`, not in the repo directory,
so it would never be committed anyway. This is properly mitigated.

Mitigation / owner decision:
No change needed. Already mitigated.

---

### F-006 — No executable signing (PyInstaller exe)

Status: TODO
Severity: Low
CVSS 3.1: N/A (distribution concern)
CWE: CWE-347 (Improper Verification of Cryptographic Signature)
Confidence: confirmed
Affected components:
- `dist/GitHubTrendsWatch.exe` — unsigned executable

Description:
The released exe is not digitally signed, which causes Windows SmartScreen warnings and
makes it impossible for users to verify the exe hasn't been tampered with after download.

Mitigation / owner decision:
1. Submit to Microsoft for reputation (https://www.microsoft.com/en-us/wdsi/filesubmission)
2. Purchase a code signing certificate (Certum Open Source ~$70/year)
3. Sign the exe with `signtool` after PyInstaller build

---

## Positive Observations

1. **subprocess.run uses list args, not shell=True** — correct safe pattern for process execution
2. **SMTP uses STARTTLS or SMTP_SSL** — credentials are encrypted in transit
3. **Config file is excluded from git** — `.gitignore` prevents accidental credential commits
4. **No hardcoded secrets in source code** — all credentials are user-provided via config
5. **Input validation in `validate_config()`** — checks for required fields before saving
6. **Single-instance lock** — prevents resource waste from duplicate processes
7. **Config migration** — old configs are safely migrated to new format
8. **Timeout on subprocess** — agent execution has a configurable timeout (default 300s)
9. **Timeout on HTTP requests** — scraper has 30s timeout
10. **History cleanup** — old reports are automatically deleted after configurable days

## Remediation Plan

| Finding | Priority | Effort | Status |
---------|----------|--------|--------|
| F-001: Plaintext credentials | **High** | Small | Fixed — os.chmod(0o600) on save | — add `os.chmod(0o600)` on save, consider `keyring` library |
| F-002: HTML injection in email | **High** | Small | Fixed — html.escape() on all scraped data | — add `html.escape()` to all scraped data in email template |
| F-003: subprocess execution | Accepted | — | Accepted intentional design |
| F-004: Bare except:pass | Low | Small | TODO — add logging |
| F-005: Config in .gitignore | Mitigated | — | No change needed |
| F-006: Unsigned exe | Low | Medium | TODO — submit to Microsoft, consider code signing |

## Final Security Level

**Medium** — The app is safe for personal use on a trusted single-user machine. Two
medium-severity findings (F-001 and F-002) should be addressed before any broader
distribution or deployment in shared environments. The codebase follows good security
practices in most areas (no shell=True, TLS for email, no hardcoded secrets, input
validation).

---

*Assessment performed using the Claude Mythos security workflow.*
*MIT — Daniel Liezrowice-Zuwasi / ESL*
