"""Automated privacy checks for a PUBLIC repository.

What this catches: credentials and tokens with recognisable formats, email addresses and
phone numbers in personal files, raw-feedback fields, and files in private/ that are
tracked by Git.

What it cannot catch: semantic leaks (a sentence that reveals something private in plain
words). Those rely on the prompts' rules and on you. Treat a passing check as "nothing
obvious", not as proof.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .core import Repo

SECRET_PATTERNS = {
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "OpenAI/Anthropic-style key": re.compile(r"\bsk-(ant-)?[A-Za-z0-9_\-]{24,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{10,}\b"),
    "private key block": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "hard-coded secret": re.compile(r"""(?i)["']?(api[_-]?key|secret|password|token)["']?\s*[:=]\s*["'][A-Za-z0-9_\-/+=]{16,}["']"""),
}
EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(\+?\d{1,3}[\s\-]?)?(\(?\d{3,5}\)?[\s\-]?)\d{3,4}[\s\-]?\d{3,4}(?!\d)")
ALLOWED_EMAILS = {"noreply@anthropic.com", "dsys-bot@users.noreply.github.com",
                  "northstar-bot@users.noreply.github.com"}

SCAN_SUFFIXES = {".json", ".md", ".py", ".yml", ".yaml", ".txt", ".toml", ".cfg", ".env", ".html", ".xml"}
SKIP_DIRS = {".git", "_site", "feeds", "__pycache__", ".pytest_cache", "private", "node_modules"}
# personal files: contact details here are almost certainly private
PERSONAL_DIRS = ("state", "feedback", "inbox", "config")


def _files(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix in SCAN_SUFFIXES and not (set(p.relative_to(root).parts) & SKIP_DIRS):
            yield p


def scan_repo(repo: Repo) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    root = repo.root
    for p in _files(root):
        rel = p.relative_to(root).as_posix()
        if rel.startswith("tests/"):
            continue  # tests build fake secrets at runtime to exercise this scanner
        text = p.read_text(encoding="utf-8", errors="ignore")
        for name, rx in SECRET_PATTERNS.items():
            if rx.search(text):
                errors.append(f"{rel}: looks like it contains a {name}. Remove it and rotate the credential.")
        if rel.startswith(PERSONAL_DIRS):
            for m in EMAIL.findall(text):
                if m.lower() not in ALLOWED_EMAILS:
                    errors.append(f"{rel}: contains an email address ({m}); keep contact details out of the repo")
            if rel.startswith(("feedback", "inbox")):
                for m in PHONE.finditer(text):
                    digits = re.sub(r"\D", "", m.group(0))
                    if len(digits) >= 10:
                        errors.append(f"{rel}: contains what looks like a phone number")
                        break
        if rel.startswith("feedback/") and '"raw"' in text:
            errors.append(f"{rel}: raw feedback text must not be stored; keep sanitized fields only")
    errors += tracked_private_files(root)
    return errors, warnings


def tracked_private_files(root: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files", "private"], cwd=root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    if out.returncode != 0:
        return []
    return [f"{f}: files in private/ must never be committed" for f in out.stdout.split()
            if f != "private/README.md"]
