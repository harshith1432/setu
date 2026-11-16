---
name: git-push-secret-protection
description: >-
  Strictly enforces zero-secret security before committing or pushing code to GitHub
  or remote repositories. Scans codebase for passwords, API keys, credentials, tokens,
  and sensitive configs. Automatically migrates hardcoded secrets to .env, updates
  .env.example with dummy placeholders, verifies .gitignore exclusions, and ensures only
  sanitized code is pushed.
---

# Git Push Secret Protection & Sanitization Skill

This skill strictly enforces that **NO secrets, passwords, credentials, usernames, or API keys** are ever committed or pushed to GitHub or any remote repository.

Whenever a commit or `git push` is planned or requested, follow this mandatory 5-step sanitization protocol.

---

## 🛑 Golden Rule: Zero Secrets in Git

1. **NEVER push secrets:** Never commit passwords, API keys, tokens, secret keys, or private certificates to version control.
2. **Always extract to `.env`:** All sensitive values must be stored locally in `.env` (which MUST be ignored by `.gitignore`).
3. **Template in `.env.example`:** Reference all required environment variable keys in `.env.example` with blank or dummy values (e.g. `GEMINI_API_KEY=""`).
4. **Code uses Environment Variables:** All application code must read configuration from environment variables (e.g., `os.getenv()`, `process.env`, `const String.fromEnvironment()`).
5. **Scan before Push:** Always run the secret scanner before executing `git push`. If any secret is detected, abort the push immediately and sanitize.

---

## 📋 Step-by-Step Execution Workflow

### Step 1: Pre-Scan the Codebase for Secrets

Run the bundled secret scanner script to check the codebase or specifically git-tracked files:

```bash
python .agents/skills/git-push-secret-protection/scripts/scan_secrets.py --tracked-only
```

Or for a full directory scan:
```bash
python .agents/skills/git-push-secret-protection/scripts/scan_secrets.py
```

Look for:
- API Keys (`AIza...`, `sk-...`, `ghp_...`, AWS `AKIA...`, Stripe `sk_...`)
- Passwords and User Credentials (`password = "..."`, `user:pass@host`)
- Private keys (`-----BEGIN PRIVATE KEY-----`)
- Base64-encoded Service Accounts (`ewogICJ...`)
- Webhook URLs and Bearer Tokens

---

### Step 2: Extract Secrets to `.env` & Update Code

If any sensitive values are found in code, configuration files (e.g. `render.yaml`, `docker-compose.yml`), or tests:

1. **Move to `.env`**:
   Add the secret key and value to the root `.env` file:
   ```env
   SERVICE_API_KEY="actual_secret_value_here"
   DATABASE_PASSWORD="actual_secure_password"
   ```

2. **Replace Hardcoded Value in Code**:
   - **Python**:
     ```python
     import os
     api_key = os.getenv("SERVICE_API_KEY")
     ```
   - **JavaScript / TypeScript**:
     ```javascript
     const apiKey = process.env.SERVICE_API_KEY; // or import.meta.env.VITE_SERVICE_API_KEY
     ```
   - **Flutter / Dart**:
     ```dart
     const apiKey = String.fromEnvironment('SERVICE_API_KEY');
     // or dotenv.env['SERVICE_API_KEY']
     ```
   - **Render / Cloud YAML (`render.yaml`)**:
     Use `sync: false` for sensitive environment variables instead of hardcoding values:
     ```yaml
     - key: FIREBASE_WEB_API_KEY
       sync: false
     - key: FIREBASE_SERVICE_ACCOUNT_B64
       sync: false
     ```

3. **Update `.env.example`**:
   Ensure `.env.example` lists the key with a placeholder (never the real secret):
   ```env
   SERVICE_API_KEY="your_api_key_here"
   DATABASE_PASSWORD="your_password_here"
   ```

---

### Step 3: Verify `.gitignore` Exclusions

Before staging changes, verify that `.env` and credential files are strictly ignored:

1. Verify `.gitignore` contains:
   ```gitignore
   .env
   .env.*
   *.env
   !*.example
   !*.example.*
   *service-account*.json
   *firebase-adminsdk*.json
   *.pem
   *.key
   ```
2. Verify `.env` is NOT currently tracked in git index:
   ```bash
   git ls-files --error-unmatch .env
   ```
   *If it is tracked, immediately untrack it without deleting local file:*
   ```bash
   git rm --cached .env
   ```

---

### Step 4: Verify Git Diff Before Staging / Committing

Review exact staged changes to ensure no sensitive files or lines slipped in:

```bash
git status
git diff --staged
```

Confirm:
- No `.env` is in `Changes to be committed`.
- No sensitive json/pem credentials are in `Changes to be committed`.
- No hardcoded keys/passwords exist in modified lines of code.

---

### Step 5: Safe Git Push

Once all steps pass with 0 secret warnings:
```bash
git add <only-sanitized-files>
git commit -m "feat/fix: descriptive commit message without secrets"
git push origin <branch>
```

---

## 🛠️ Quick Reference Commands

| Action | Command |
| :--- | :--- |
| **Run Secret Scanner** | `python .agents/skills/git-push-secret-protection/scripts/scan_secrets.py` |
| **Check Untracked / Staged** | `git status` |
| **Untrack `.env` if committed** | `git rm --cached .env` |
| **Verify Git Diff** | `git diff --cached` |
| **Check File Ignore Status** | `git check-ignore -v .env` |
