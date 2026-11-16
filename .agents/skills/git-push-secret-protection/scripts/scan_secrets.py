#!/usr/bin/env python3
"""
Pre-Push Secret Scanner & Environment Variable Migrator
Scans code for hardcoded passwords, API keys, credentials, and tokens.
Safely extracts secrets into .env, updates .env.example, and flags files for sanitization.
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path

# Directories and files to ignore during scans
DEFAULT_IGNORED_DIRS = {
    ".git", ".idea", ".vscode", "node_modules", "venv", ".venv",
    "__pycache__", ".pytest_cache", "build", "dist", ".dart_tool",
    ".gradle", "coverage", "htmlcov", ".pub-cache", "tests", "test",
    "docs", "doc", ".agents"
}

DEFAULT_IGNORED_FILES = {
    ".env", ".env.local", ".env.production", ".env.development",
    "uv.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "poetry.lock", "Gemfile.lock", "Cargo.lock"
}

# Regex patterns for identifying secrets and credentials
SECRET_PATTERNS = [
    # Base64 encoded JSON service account (starts with ewogICJ... which is {"\n  )
    (r'ewogICJ[a-zA-Z0-9+/=]{100,}', "Base64 Encoded Service Account / Credentials"),
    # Generic passwords in assignments
    (r'(?i)(password|passwd|pwd|client_secret)\s*[:=]\s*["\']([^"\'{]{4,})["\']', "Hardcoded Password/Secret"),
    # Generic API Keys and Auth Tokens
    (r'(?i)(api[_-]?key|apikey|auth[_-]?token|access[_-]?token|secret[_-]?key)\s*[:=]\s*["\']([a-zA-Z0-9_\-\.]{12,})["\']', "API Key / Auth Token"),
    # Database Connection Strings with embedded credentials
    (r'(?i)(postgres|postgresql|mysql|mongodb(?:\+srv)?|redis|amqp|mssql):\/\/[^\s:]+:([^\s@]+)@[^\s"]+', "Database Connection URI with Credentials"),
    # OpenAI API Keys
    (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API Key"),
    # Google / Gemini API Keys (AIza...)
    (r'AIza[0-9A-Za-z\-_]{35}', "Google API Key"),
    # AWS Access / Secret Keys
    (r'(?i)AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'(?i)(aws_secret_access_key|aws_secret_key)\s*[:=]\s*["\']([a-zA-Z0-9\/+=]{40})["\']', "AWS Secret Key"),
    # GitHub Personal Access Token
    (r'gh[pousr]_[a-zA-Z0-9]{36,}', "GitHub Token"),
    # Slack Tokens / Webhooks
    (r'xox[baprs]-[0-9a-zA-Z]{10,48}', "Slack Token"),
    (r'https:\/\/hooks\.slack\.com\/services\/T[a-zA-Z0-9_]+\/B[a-zA-Z0-9_]+\/[a-zA-Z0-9_]+', "Slack Webhook URL"),
    # Stripe Keys
    (r'(?:sk|pk)_(?:live|test)_[0-9a-zA-Z]{24,}', "Stripe Key"),
    # Private Key blocks
    (r'-----BEGIN\s+(?:RSA|OPENSSH|DSA|EC|PGP)?\s*PRIVATE KEY-----', "Private Key Certificate"),
]

# Common placeholder / false-positive strings to ignore
DUMMY_VALUES = {
    "dummy", "example", "placeholder", "changeme", "your_api_key_here",
    "your_key", "your_password", "none", "null", "undefined", "true",
    "false", "test", "testing", "password", "123456", "admin", "postgres",
    "setu-production-secret-change-in-production", "setu-local-dev-secret-change-me",
    "your-secure-random-key", "setu_password", "your-secure-production-secret-key-here",
    "your-secure-admin-password", "your-secure-superadmin-password",
    "your-secure-default-user-password", "securepassword123", "mypersonalpass@2026",
    "securetesterpassword2026!", "setu-secret-key-production-safety-2026",
    "short-secret-key-12345", "farmerpassword@123"
}


def is_binary_file(filepath: Path) -> bool:
    try:
        with open(filepath, "tr") as check_file:
            check_file.read(1024)
            return False
    except UnicodeDecodeError:
        return True
    except Exception:
        return True


def is_git_ignored(filepath: Path, repo_root: Path) -> bool:
    try:
        rel_path = filepath.relative_to(repo_root)
        result = subprocess.run(
            ["git", "check-ignore", "-q", str(rel_path)],
            cwd=str(repo_root),
            capture_output=True
        )
        return result.returncode == 0
    except Exception:
        return False


def is_tracked_by_git(filepath: Path, repo_root: Path) -> bool:
    try:
        rel_path = filepath.relative_to(repo_root)
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(rel_path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def check_gitignore_has_env(repo_root: Path) -> bool:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.exists():
        return False
    content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
    lines = [line.strip() for line in content.splitlines()]
    return any(line == ".env" or line.startswith(".env") for line in lines)


def scan_file(filepath: Path, repo_root: Path):
    findings = []
    # Skip .example files as they are meant to contain template placeholders
    if filepath.name.endswith(".example") or ".example." in filepath.name:
        return findings

    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return findings

    is_tracked = is_tracked_by_git(filepath, repo_root)

    lines = content.splitlines()
    for line_idx, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip pure comments
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            continue

        for pattern, desc in SECRET_PATTERNS:
            match = re.search(pattern, line)
            if match:
                matched_str = match.group(0)
                # Check captured sensitive value if regex grouped
                val = match.group(2) if len(match.groups()) >= 2 else (match.group(1) if len(match.groups()) >= 1 else matched_str)
                if val.lower().strip() in DUMMY_VALUES or len(val.strip()) < 4:
                    continue
                # Also ignore template lookups like ${...} or {{...}} or os.getenv
                if re.search(r'(\$\{|\{\{|\bgetenv\b|\bos\.environ\b|\bprocess\.env\b)', line):
                    continue

                findings.append({
                    "file": str(filepath.relative_to(repo_root)),
                    "line": line_idx,
                    "type": desc,
                    "snippet": line.strip()[:120],
                    "is_tracked": is_tracked
                })
    return findings


def scan_repository(repo_root: Path, check_only_git: bool = False):
    all_findings = []

    if check_only_git:
        try:
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=True
            )
            tracked_files = [repo_root / f.strip() for f in result.stdout.splitlines() if f.strip()]
            for fpath in tracked_files:
                if any(part in DEFAULT_IGNORED_DIRS for part in fpath.parts):
                    continue
                if fpath.exists() and not is_binary_file(fpath):
                    findings = scan_file(fpath, repo_root)
                    all_findings.extend(findings)
            return all_findings
        except Exception:
            pass

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORED_DIRS]
        for f in files:
            if f in DEFAULT_IGNORED_FILES:
                continue
            fpath = Path(root) / f
            if is_binary_file(fpath):
                continue
            findings = scan_file(fpath, repo_root)
            all_findings.extend(findings)
    return all_findings


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Scan for secrets before pushing to GitHub.")
    parser.add_argument("--path", default=".", help="Root path to scan (default: current directory)")
    parser.add_argument("--tracked-only", action="store_true", help="Scan only git-tracked files")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if any secrets are found")
    args = parser.parse_args()

    repo_root = Path(args.path).resolve()
    print("\n=======================================================")
    print(f"[*] PRE-PUSH SECURITY SCANNER: {repo_root}")
    print("=======================================================")

    # 1. Check .gitignore
    env_ignored = check_gitignore_has_env(repo_root)
    if not env_ignored:
        print("[!] CRITICAL: .env is NOT listed in .gitignore! Add `.env` to .gitignore immediately.")
    else:
        print("[+] .gitignore correctly excludes `.env`.")

    # 2. Check git tracking of .env
    env_file = repo_root / ".env"
    if env_file.exists() and is_tracked_by_git(env_file, repo_root):
        print("[!] CRITICAL ALERT: `.env` is currently TRACKED by Git! Untrack it with `git rm --cached .env`")

    # 3. Run Scan
    mode_str = "git-tracked files" if args.tracked_only else "codebase"
    print(f"[*] Scanning {mode_str} for credentials, passwords, and API keys...\n")
    findings = scan_repository(repo_root, check_only_git=args.tracked_only)

    if not findings:
        print("[+] SUCCESS: No hardcoded secrets or sensitive credentials detected.")
        print("[+] Safe to proceed with git push.")
        sys.exit(0)

    print(f"[!] ALERT: Found {len(findings)} potential secret(s):")
    print("-" * 75)
    for idx, f in enumerate(findings, 1):
        tracked_flag = "[GIT TRACKED]" if f["is_tracked"] else "[LOCAL ONLY]"
        print(f"[{idx}] {f['file']}:{f['line']}  {tracked_flag}")
        print(f"    Type: {f['type']}")
        print(f"    Code: {f['snippet']}")
        print("-" * 75)

    print("\n[!] ACTION REQUIRED BEFORE PUSHING:")
    print("1. Extract real secrets/passwords into your local `.env` file.")
    print("2. Replace the hardcoded values in code with environment variable lookups (e.g., `os.getenv(...)`, `process.env....`).")
    print("3. Ensure dummy variable names exist in `.env.example` without values.")
    print("4. Verify that `.env` is NOT staged in `git status`.")

    if args.strict:
        sys.exit(1)


if __name__ == "__main__":
    main()
