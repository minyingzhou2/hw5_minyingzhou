---
name: job-fit-scanner
description: Use this skill when the user wants to compare a resume against a job description, estimate job fit, identify missing keywords, highlight aligned strengths, or produce a reusable resume-tailoring checklist. It is especially relevant when the user provides text files or asks for an ATS-style match report, keyword gap analysis, or evidence-backed fit summary.
---

# Job Fit Scanner

This skill turns a plain-text or markdown resume and a plain-text or markdown job description into a deterministic fit report.

## When to use this skill
- The user asks how well a resume matches a job description.
- The user wants an ATS-style scan, keyword gap analysis, or fit score.
- The user wants evidence-backed recommendations for truthful resume tailoring.
- The user provides a resume file and a JD file and wants structured comparison output.

## When not to use this skill
- Do not use it for generic cover-letter writing without a resume/JD comparison task.
- Do not use it to guarantee interview odds, predict hiring outcomes, or fabricate a “real ATS score.”
- Do not use it if the only available files are images or PDFs that have not been converted to text yet.
- Do not invent missing experience to improve the score.

## Expected inputs
- One resume file in `.txt` or `.md`
- One job description file in `.txt` or `.md`
- Optional request for output format or follow-up explanation

## Available script
- `scripts/job_fit_scanner.py` — parses both files, extracts requirement signals, computes a reproducible weighted match score, and formats the result as markdown or JSON.

## Workflow
1. Confirm the user has supplied a resume file and a job description file in `.txt` or `.md`.
2. Run the script from the skill root.

```bash
python3 scripts/job_fit_scanner.py --resume <resume_file> --job <job_file>
```

3. Read the generated report.
4. Summarize the result for the user in plain English:
   - overall match score
   - strongest overlaps
   - missing or weakly supported requirements
   - 2-4 truthful tailoring suggestions
5. If the user asks for machine-readable output, rerun in JSON mode.

```bash
python3 scripts/job_fit_scanner.py --resume <resume_file> --job <job_file> --format json
```

## Required checks
- Use only evidence present in the resume text.
- Treat the score as a heuristic, not a guarantee.
- If the script flags weak evidence or incomplete files, mention that clearly.
- If the user asks you to “add” missing qualifications they do not have, refuse and suggest truthful reframing instead.

## Output format
Default user-facing output should follow this structure:
1. One-sentence fit summary
2. Match score and weighted coverage
3. Top aligned strengths
4. Missing or weakly supported requirements
5. Truthful next-step recommendations

For a fuller template, see `references/output-template.md`.

## Gotchas
- The script only supports `.txt` and `.md` inputs.
- The fit score is deterministic for the same inputs, but it is not a vendor ATS replica.
- Short or partial job descriptions can understate or distort requirement coverage.
- Some soft skills may be partially captured through wording, so explain uncertainty when needed.
