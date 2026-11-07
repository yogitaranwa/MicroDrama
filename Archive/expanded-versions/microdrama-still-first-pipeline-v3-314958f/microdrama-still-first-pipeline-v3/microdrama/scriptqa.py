from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FRAGMENT_WORDS = {
    "Efficient.", "Show-off.", "Show off.", "You didn't.", "Then count faster.",
}

@dataclass(frozen=True)
class ScriptIssue:
    severity: str
    message: str


def dialogue_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for match in re.finditer(r'(?:DRACONIA|HARRY):\s*"([^"]+)"', markdown):
        lines.append(match.group(1).strip())
    return lines


def validate_script_text(markdown: str) -> list[ScriptIssue]:
    issues: list[ScriptIssue] = []
    lines = dialogue_lines(markdown)
    if not lines:
        issues.append(ScriptIssue("error", "No dialogue lines found"))
        return issues
    for stamp in re.findall(r"\b(\d+):(\d{2})\b", markdown):
        minute, second = map(int, stamp)
        if second >= 60:
            issues.append(ScriptIssue("error", f"Invalid time notation: {minute}:{second:02d}"))
    for line in lines:
        words = re.findall(r"[A-Za-z']+", line)
        if line in FRAGMENT_WORDS:
            issues.append(ScriptIssue("error", f"Rejected fragment from v2 remains: {line}"))
        if len(words) < 4:
            issues.append(ScriptIssue("error", f"Dialogue is too short to feel human: {line}"))
        if len(words) > 28:
            issues.append(ScriptIssue("warning", f"Dialogue may be overexplaining: {line}"))
        if not re.search(r"\b(I|you|we|me|us|Potter|dance|curse|waltz|plan|warn|follow|take|cut|trust|know)\b", line, re.I):
            issues.append(ScriptIssue("warning", f"Dialogue may lack human intent: {line}"))
    return issues


def validate_script_file(path: str | Path) -> list[ScriptIssue]:
    return validate_script_text(Path(path).read_text())
