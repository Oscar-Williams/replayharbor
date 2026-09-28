"""Scan publishable working files, index blobs and reachable Git history.

Reports paths and rule names only. This is a focused guard, not a complete DLP system.
"""
import re
import subprocess
from pathlib import Path

RULES = {
    "api-token": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
    "github-token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "bearer-value": re.compile(rb"Bearer\s+[A-Za-z0-9_.-]{24,}"),
    "credential-assignment": re.compile(rb"(?im)^[ \t]*(?:DEEPSEEK_API_KEY|OPENAI_API_KEY|API_KEY|GITHUB_TOKEN)[ \t]*=[ \t]*[^\s#\r\n][^\r\n]{7,}"),
}


def findings(data):
    return [name for name, pattern in RULES.items() if pattern.search(data)]


def private_name(name):
    parts = Path(name).parts
    return any((p == ".env" or p.startswith(".env.")) and p != ".env.example" for p in parts) or any(p in {"secrets", "private"} for p in parts) or name.endswith((".pem", ".key"))


def scan(root):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL)
    issues = []
    files = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")
    for entry in sorted(set(files)-{b""}):
        name = entry.decode("utf-8")
        path = root / name
        if private_name(name):
            issues.append(("working:"+name,"private-file"))
        if path.is_symlink() or (path.exists() and not path.resolve().is_relative_to(root.resolve())):
            issues.append(("working:"+name,"external-link"))
            continue
        if path.is_file():
            issues.extend(("working:"+name, rule) for rule in findings(path.read_bytes()))
    # Check staged content, even when the working copy has already been cleaned.
    for entry in git("ls-files", "-z").split(b"\0"):
        if not entry:
            continue
        name = entry.decode("utf-8")
        issues.extend(("index:"+name, rule) for rule in findings(git("show", ":"+name)))
    commits = git("rev-list", "--all").decode().splitlines()
    seen = set()
    for commit in commits:
        for entry in git("ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
            if not entry:
                continue
            meta, name = entry.split(b"\t",1)
            _, kind, blob = meta.split()
            name = name.decode("utf-8")
            if private_name(name):
                issues.append(("history:"+name,"private-file"))
            if kind == b"blob" and blob not in seen:
                seen.add(blob)
                issues.extend(("history:"+name, rule) for rule in findings(git("cat-file", "blob", blob.decode())))
    return sorted(set(issues))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    try:
        result = scan(root)
    except (OSError, subprocess.CalledProcessError):
        print("FAIL: scanner could not inspect all requested Git data")
        raise SystemExit(2)
    for path, rule in result:
        print(f"BLOCK {path} [{rule}]")
    print("PASS: no configured secret patterns found" if not result else "FAIL: resolve findings before commit or push")
    raise SystemExit(bool(result))
