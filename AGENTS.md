# Workspace Rules: Zero Secrets in Git & Pre-Push Sanitization

## 🛑 MANDATORY PRE-PUSH RULE: NEVER PUSH SECRETS TO GIT

Whenever committing or pushing code to GitHub or any remote repository, the agent MUST strictly enforce zero-secret security:

1. **Strict Prohibition:**
   - NEVER commit or push passwords, credentials, usernames, API keys, tokens, secret keys, or private certificates.
   - Files like `.env`, `.env.*`, `*service-account*.json`, and `*.pem` must NEVER be tracked by Git.

2. **Mandatory Secret Scan:**
   - Before executing `git commit` or `git push`, run the security scanner:
     ```bash
     python .agents/skills/git-push-secret-protection/scripts/scan_secrets.py --tracked-only
     ```
   - If ANY secrets are detected:
     1. Immediately halt the commit/push.
     2. Move the sensitive values to the local `.env` file.
     3. Replace hardcoded values in code/configs with environment variable lookups (`os.getenv()`, `process.env`, `String.fromEnvironment()`).
     4. Put blank/dummy placeholders in `.env.example`.
     5. Verify that `.env` is in `.gitignore` and not tracked in `git status`.

3. **Verify Git Staging:**
   - Always run `git status` and `git diff --staged` before committing.
   - Confirm that only clean, sanitized code is committed.
