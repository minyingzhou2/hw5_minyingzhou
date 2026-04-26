#!/usr/bin/env python3
"""Deterministic resume-to-job fit scanner for agent skills.

The script compares a plain-text or markdown resume with a job description,
extracts requirement signals, computes a reproducible match score, and emits a
structured report in markdown or JSON.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

CANONICAL_SKILLS = {
    "python": [r"\bpython\b"],
    "sql": [r"\bsql\b", r"postgres(?:ql)?", r"mysql", r"sqlite", r"snowflake", r"bigquery"],
    "excel": [r"\bexcel\b"],
    "power bi": [r"power\s*bi"],
    "tableau": [r"\btableau\b"],
    "pandas": [r"\bpandas\b"],
    "numpy": [r"\bnumpy\b"],
    "scikit-learn": [r"scikit[-\s]?learn", r"sklearn"],
    "machine learning": [r"machine learning", r"predictive model", r"classification", r"regression model"],
    "llm / genai": [r"\bllm\b", r"generative ai", r"genai", r"prompt engineering", r"agentic ai", r"ai agent"],
    "statistics": [r"\bstatistics\b", r"hypothesis testing", r"a/?b testing"],
    "data visualization": [r"data visuali[sz]ation", r"dashboard", r"dashboards", r"storytelling with data"],
    "forecasting": [r"forecast", r"time series", r"arima", r"arma", r"kpss", r"adf test"],
    "etl / data pipelines": [r"\betl\b", r"data pipeline", r"data pipelines", r"pipeline automation"],
    "api": [r"\bapi\b", r"rest api", r"api integration"],
    "experimentation": [r"experiment", r"experimentation", r"a/?b testing"],
    "communication": [r"communication", r"present(ed|ation)?", r"stakeholder", r"cross-functional", r"storytelling"],
    "project management": [r"project management", r"manage(d|ment)?", r"coordinate(d)?", r"timeline"],
    "customer analytics": [r"customer analytics", r"customer health", r"retention", r"churn"],
    "marketing analytics": [r"marketing analytics", r"campaign analysis", r"ad platform", r"advertising analytics"],
}

PRIORITY_HINTS = {
    "required": 1.25,
    "must": 1.25,
    "minimum": 1.15,
    "preferred": 0.85,
    "plus": 0.75,
    "nice to have": 0.70,
}

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
BULLET_SPLIT = re.compile(r"(?:^|\n)\s*(?:[-*•]|\d+[.)])\s+")
LINE_SPLIT = re.compile(r"\n+")
WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z+/#.-]{1,}")
STOPWORDS = {
    "and", "the", "for", "with", "that", "this", "from", "your", "you", "are", "our",
    "will", "into", "using", "use", "used", "have", "has", "had", "their", "they", "them",
    "job", "role", "team", "work", "works", "working", "skills", "skill", "years", "year",
    "experience", "preferred", "required", "plus", "about", "ability", "strong", "highly",
    "seeking", "candidate", "intern", "analyst", "data", "business", "support", "build",
}


@dataclass
class Requirement:
    label: str
    evidence: str
    weight: float
    source: str
    matched: bool = False
    matched_evidence: str | None = None


@dataclass
class Report:
    resume_path: str
    job_path: str
    match_score: int
    coverage_ratio: float
    matched_requirements: list[dict]
    missing_requirements: list[dict]
    matched_skills: list[str]
    missing_skills: list[str]
    top_resume_strengths: list[str]
    caution_flags: list[str]


def read_text(path: Path) -> str:
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ValueError(
            f"Unsupported file type: {path.suffix or '<none>'}. "
            "Use plain-text or markdown files for this skill."
        )
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Input file is empty: {path}")
    return text


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_units(text: str) -> list[str]:
    bullets = [normalize_space(x) for x in BULLET_SPLIT.split("\n" + text) if normalize_space(x)]
    lines = [normalize_space(x) for x in LINE_SPLIT.split(text) if normalize_space(x)]
    sents = [normalize_space(x) for x in SENTENCE_SPLIT.split(text) if normalize_space(x)]
    units = bullets + [x for x in lines if x not in bullets] + [s for s in sents if s not in bullets and s not in lines]
    return units


def canonical_skill_hits(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for skill, patterns in CANONICAL_SKILLS.items():
        for pat in patterns:
            m = re.search(pat, text, flags=re.I)
            if m:
                hits.setdefault(skill, []).append(m.group(0))
    return hits


def infer_weight(text: str) -> float:
    lower = text.lower()
    weight = 1.0
    for hint, factor in PRIORITY_HINTS.items():
        if hint in lower:
            weight = max(weight, factor)
    return weight


def is_redundant_phrase(label: str, seen: set[str]) -> bool:
    phrase_hits = set(canonical_skill_hits(label).keys())
    if phrase_hits and phrase_hits.issubset(seen):
        return True
    return False


def extract_requirements(job_text: str) -> list[Requirement]:
    units = split_units(job_text)
    reqs: list[Requirement] = []
    skill_hits = canonical_skill_hits(job_text)

    # Skill-driven requirements
    for skill in sorted(skill_hits):
        hit_text = ", ".join(sorted(set(skill_hits[skill])))
        source = next((u for u in units if re.search(rf"\b{re.escape(hit_text.split(',')[0])}\b", u, flags=re.I)), hit_text)
        reqs.append(Requirement(label=skill, evidence=hit_text, weight=infer_weight(source), source=source))

    # Requirement phrases that may not map cleanly to the skills dictionary.
    phrase_patterns = [
        r"(?:experience|proficiency|proficient|knowledge|familiarity)\s+(?:with|in)\s+([A-Za-z0-9+/# .-]{3,80})",
        r"ability\s+to\s+([A-Za-z0-9+/# ,.-]{3,80})",
        r"responsible\s+for\s+([A-Za-z0-9+/# ,.-]{3,80})",
    ]
    seen = {r.label for r in reqs}
    for unit in units:
        for pat in phrase_patterns:
            for m in re.finditer(pat, unit, flags=re.I):
                phrase = normalize_space(m.group(1)).strip(" .,:;-")
                if len(phrase) < 4:
                    continue
                label = phrase.lower()
                if is_redundant_phrase(label, seen):
                    continue
                if label not in seen and len(seen) < 18:
                    reqs.append(Requirement(label=label, evidence=phrase, weight=infer_weight(unit), source=unit))
                    seen.add(label)

    # Keep highest-weighted unique requirements.
    deduped: dict[str, Requirement] = {}
    for req in reqs:
        current = deduped.get(req.label)
        if current is None or req.weight > current.weight:
            deduped[req.label] = req
    return sorted(deduped.values(), key=lambda r: (-r.weight, r.label))[:18]


def find_resume_evidence(resume_text: str, label: str) -> str | None:
    units = split_units(resume_text)
    patterns = CANONICAL_SKILLS.get(label, [re.escape(label)])
    for unit in units:
        for pat in patterns:
            if re.search(pat, unit, flags=re.I):
                return unit
    # fallback for multiword phrase partial matching
    label_terms = [t for t in re.findall(r"[a-zA-Z]{3,}", label.lower()) if t not in STOPWORDS]
    if label_terms:
        for unit in units:
            unit_lower = unit.lower()
            overlap = sum(1 for term in label_terms if term in unit_lower)
            if overlap >= max(1, min(2, len(label_terms))):
                return unit
    return None


def top_strengths(resume_text: str, limit: int = 5) -> list[str]:
    hits = canonical_skill_hits(resume_text)
    skills = sorted(hits.keys())
    if skills:
        return skills[:limit]
    words = [w.lower() for w in WORD_RE.findall(resume_text) if w.lower() not in STOPWORDS and len(w) > 3]
    return [w for w, _ in Counter(words).most_common(limit)]


def caution_flags(job_text: str, resume_text: str, matched: list[Requirement], missing: list[Requirement]) -> list[str]:
    flags: list[str] = []
    if len(resume_text) < 500:
        flags.append("Resume text is short; the score may understate fit because there is limited evidence to scan.")
    if len(job_text) < 500:
        flags.append("Job description is short or partial; missing requirements may not reflect the full role.")
    if any(x.label in {"python", "sql", "machine learning"} for x in missing):
        flags.append("One or more core technical requirements appear missing; tailor the resume carefully before using this report.")
    if not matched:
        flags.append("No reliable overlap detected. Check file quality, formatting, or whether the role is outside the resume's domain.")
    return flags


def build_report(resume_path: Path, job_path: Path) -> Report:
    resume_text = read_text(resume_path)
    job_text = read_text(job_path)

    requirements = extract_requirements(job_text)
    if not requirements:
        raise ValueError("Could not extract enough requirements from the job description.")

    matched: list[Requirement] = []
    missing: list[Requirement] = []
    total_weight = sum(r.weight for r in requirements)
    matched_weight = 0.0

    for req in requirements:
        evidence = find_resume_evidence(resume_text, req.label)
        if evidence:
            req.matched = True
            req.matched_evidence = evidence
            matched.append(req)
            matched_weight += req.weight
        else:
            missing.append(req)

    score = round((matched_weight / total_weight) * 100) if total_weight else 0
    report = Report(
        resume_path=str(resume_path),
        job_path=str(job_path),
        match_score=score,
        coverage_ratio=round(matched_weight / total_weight, 3) if total_weight else 0.0,
        matched_requirements=[asdict(r) for r in matched],
        missing_requirements=[asdict(r) for r in missing],
        matched_skills=sorted({r.label for r in matched}),
        missing_skills=sorted({r.label for r in missing}),
        top_resume_strengths=top_strengths(resume_text),
        caution_flags=caution_flags(job_text, resume_text, matched, missing),
    )
    return report


def to_markdown(report: Report) -> str:
    lines = [
        "# Job Fit Scan",
        "",
        f"- **Resume:** `{report.resume_path}`",
        f"- **Job description:** `{report.job_path}`",
        f"- **Match score:** **{report.match_score}/100**",
        f"- **Weighted coverage:** `{report.coverage_ratio:.1%}`",
        "",
        "## Top resume strengths",
    ]
    for item in report.top_resume_strengths:
        lines.append(f"- {item}")

    lines += ["", "## Matched requirements"]
    if report.matched_requirements:
        lines.append("| Requirement | Weight | Resume evidence |")
        lines.append("|---|---:|---|")
        for item in report.matched_requirements:
            lines.append(
                f"| {item['label']} | {item['weight']:.2f} | {item['matched_evidence'].replace('|', '/')} |"
            )
    else:
        lines.append("- None")

    lines += ["", "## Missing or weakly supported requirements"]
    if report.missing_requirements:
        lines.append("| Requirement | Weight | Job evidence |")
        lines.append("|---|---:|---|")
        for item in report.missing_requirements:
            lines.append(
                f"| {item['label']} | {item['weight']:.2f} | {item['source'].replace('|', '/')} |"
            )
    else:
        lines.append("- None")

    lines += ["", "## Caution flags"]
    if report.caution_flags:
        lines.extend(f"- {flag}" for flag in report.caution_flags)
    else:
        lines.append("- None")

    lines += ["", "## Suggested next step", "- Use the missing requirements list to tailor bullets truthfully; do not invent experience."]
    return "\n".join(lines) + "\n"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare a plain-text resume with a plain-text job description and produce a deterministic fit report."
    )
    parser.add_argument("--resume", required=True, help="Path to a .txt or .md resume file")
    parser.add_argument("--job", required=True, help="Path to a .txt or .md job description file")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--out", help="Optional output file path")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    try:
        report = build_report(Path(args.resume), Path(args.job))
        output = to_markdown(report) if args.format == "markdown" else json.dumps(asdict(report), indent=2)
        if args.out:
            Path(args.out).write_text(output, encoding="utf-8")
        else:
            sys.stdout.write(output)
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"ERROR: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
